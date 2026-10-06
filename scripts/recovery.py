#!/usr/bin/env python3
"""Preflight the existing in-place recovery flow; mutations require --execute."""
import argparse
from contextlib import contextmanager
import os
import shlex
import sys
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=660)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Recovery command timed out") from None
    if result.returncode:
        # Command output may contain credentials. Keep errors bounded to the operation.
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd[:3])}")
    return result.stdout


def read_json(cmd):
    return json.loads(run(cmd))


def timestamp(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
        raise ValueError("recovery-time must be YYYY-MM-DD HH:MM:SS (UTC)")
    target = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    if target > datetime.now(timezone.utc):
        raise ValueError("recovery-time must not be in the future")
    return target


def identifier(value, maximum=53):
    if len(value) > maximum or not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", value):
        raise ValueError("Invalid namespace or Helm release name")
    return value


def owned(resource, release, namespace):
    meta = resource.get("metadata", {})
    annotations = meta.get("annotations", {})
    if (meta.get("namespace") != namespace or annotations.get("meta.helm.sh/release-name") != release
            or annotations.get("meta.helm.sh/release-namespace") != namespace):
        raise ValueError("Resource does not belong to the expected Helm release/namespace")


def select_pvcs(items, release, namespace, cluster):
    expected = {"application": "patroni", "release-name": release, "cluster-name": cluster}
    selected = []
    prefix = f"pgdata-{cluster}-"
    for pvc in items:
        meta = pvc["metadata"]
        labels = meta.get("labels", {})
        name = meta["name"]
        if not (name.startswith(prefix) or labels.get("release-name") == release):
            continue
        if meta.get("namespace") != namespace or any(labels.get(k) != v for k, v in expected.items()):
            raise ValueError("Ambiguous PVC ownership; refusing recovery")
        if not re.fullmatch(re.escape(prefix) + r"\d+", name):
            raise ValueError("Unexpected PVC name for this cluster")
        annotations = meta.get("annotations", {})
        if annotations.get("meta.helm.sh/release-name", release) != release:
            raise ValueError("PVC belongs to another release")
        if meta.get("deletionTimestamp") or pvc.get("status", {}).get("phase") != "Bound":
            raise ValueError("PVC is not stably Bound")
        selected.append(pvc)
    if not selected:
        raise ValueError("No PostgreSQL PVCs found; refusing recovery")
    return sorted(selected, key=lambda x: x["metadata"]["name"])


def select_backup(backups, target, cluster, requested=None):
    eligible = []
    for backup in backups:
        name = backup.get("backup_name", "")
        if not re.fullmatch(r"base_[A-Za-z0-9_]+", name):
            continue
        if requested and name != requested:
            continue
        # --detail is required: do not substitute upload time for backup completion.
        finish = backup.get("finish_time")
        host = backup.get("hostname", "")
        if not finish or not re.fullmatch(re.escape(cluster) + r"-\d+", host):
            continue
        end = datetime.fromisoformat(finish.replace("Z", "+00:00"))
        if end.tzinfo is None:
            continue
        if end <= target:
            eligible.append((end, name))
    if not eligible:
        raise ValueError("No identifiable backup from this cluster completed before target time")
    return max(eligible)[1]


def preflight(args):
    target = timestamp(args.recovery_time)
    ns = identifier(args.namespace, 63)
    release = identifier(args.patroni_releasename)
    pgcat = identifier(args.pgcat_releasename)
    cluster = f"{release}-patronimvp"
    kube = ["kubectl", "-n", ns]
    namespace = read_json(["kubectl", "get", "namespace", ns, "-o", "json"])
    if namespace.get("metadata", {}).get("name") != ns:
        raise ValueError("Unexpected namespace response")
    for name in [release, pgcat]:
        status = read_json(["helm", "status", name, "-n", ns, "-o", "json"])
        if status.get("name") != name or status.get("namespace") != ns or status.get("info", {}).get("status") != "deployed":
            raise ValueError("Expected a deployed Helm release in the target namespace")
    sts = read_json(kube + ["get", "statefulset", cluster, "-o", "json"])
    owned(sts, release, ns)
    retention = sts["spec"].get("persistentVolumeClaimRetentionPolicy", {})
    if any(retention.get(key, "Retain") != "Retain" for key in ("whenScaled", "whenDeleted")):
        raise ValueError("Recovery requires retained PVCs during shutdown and uninstall")
    selector = {"application": "patroni", "release-name": release, "cluster-name": cluster}
    if sts["spec"]["selector"]["matchLabels"] != selector:
        raise ValueError("Unexpected PostgreSQL StatefulSet selector")
    for role, suffix in [("primary", "master"), ("replica", "replica")]:
        service = read_json(kube + ["get", "service", f"patronimvp-{suffix}-{release}", "-o", "json"])
        owned(service, release, ns)
        if service.get("spec", {}).get("selector") != {**selector, "role": role}:
            raise ValueError("PostgreSQL Service selector does not identify the expected cluster/role")
    claims = sts["spec"]["volumeClaimTemplates"]
    if len(claims) != 1 or claims[0]["metadata"]["name"] != "pgdata":
        raise ValueError("Unexpected volume layout")
    proxy = read_json(kube + ["get", "deployment", f"{pgcat}-proxy-deployment", "-o", "json"])
    owned(proxy, pgcat, ns)
    values = {name: read_json(["helm", "get", "values", name, "-n", ns, "--all", "-o", "json"]) for name in [release, pgcat]}
    if not values[release].get("security", {}).get("allowInlineSecrets", True) or values[release].get("postgres", {}).get("existingSecret"):
        pg_secret_name = values[release].get("postgres", {}).get("existingSecret") or f"{release}-postgres-credentials"
        credentials = read_json(kube + ["get", "secret", pg_secret_name, "-o", "json"])
        if credentials.get("metadata", {}).get("namespace") != ns or not all(credentials.get("data", {}).get(k) for k in ["superuser-username", "superuser-password", "replication-username", "replication-password"]):
            raise ValueError("PostgreSQL credential Secret is incomplete")
        refs = {e.get("valueFrom", {}).get("secretKeyRef", {}).get("name") for c in sts["spec"]["template"]["spec"]["containers"] for e in c.get("env", [])}
        if pg_secret_name not in refs:
            raise ValueError("PostgreSQL credential Secret does not match StatefulSet")
    if not values[pgcat].get("security", {}).get("allowInlineSecrets", True) or values[pgcat].get("pgadmin", {}).get("existingSecret"):
        admin_name = values[pgcat].get("pgadmin", {}).get("existingSecret") or f"{pgcat}-pgadmin"
        admin = read_json(kube + ["get", "secret", admin_name, "-o", "json"])
        if admin.get("metadata", {}).get("namespace") != ns or not admin.get("data", {}).get("pgadmin-password"):
            raise ValueError("pgAdmin credential Secret is incomplete")
    proxy_secret_name = values[pgcat].get("existingSecret") or f"{pgcat}-pgcat-config"
    proxy_secret = read_json(kube + ["get", "secret", proxy_secret_name, "-o", "json"])
    if values[pgcat].get("security", {}).get("allowInlineSecrets", True) and not values[pgcat].get("existingSecret"):
        owned(proxy_secret, pgcat, ns)
    elif (proxy_secret.get("metadata", {}).get("namespace") != ns or proxy_secret_name not in {v.get("secret", {}).get("secretName") for v in proxy["spec"]["template"]["spec"].get("volumes", [])}):
        raise ValueError("External PgCat Secret does not match deployment")
    pgcat_config = yaml.safe_load(base64.b64decode(proxy_secret.get("data", {}).get("pgcat.yaml", "")))
    if not isinstance(pgcat_config, dict) or not pgcat_config.get("DBS"):
        raise ValueError("PgCat configuration is missing")
    for database in pgcat_config["DBS"]:
        if not database.get("shards"):
            raise ValueError("PgCat backend configuration is missing")
        for shard in database["shards"]:
            if shard.get("MASTER_HOST") != f"patronimvp-master-{release}" or (shard.get("INCLUDE_REPLICA", True) and shard.get("REPLICA_HOST") != f"patronimvp-replica-{release}"):
                raise ValueError("PgCat backend points outside the intended PostgreSQL cluster")
    walg_secret_name = values[release].get("walg", {}).get("existingSecret") or f"{release}-wal-g-credentials"
    secret = read_json(kube + ["get", "secret", walg_secret_name, "-o", "json"])
    inline = values[release].get("security", {}).get("allowInlineSecrets", True) and not values[release].get("walg", {}).get("existingSecret")
    if inline:
        owned(secret, release, ns)
    elif (secret.get("metadata", {}).get("namespace") != ns or walg_secret_name not in {v.get("secret", {}).get("secretName") for v in sts["spec"]["template"]["spec"].get("volumes", [])}):
        raise ValueError("External WAL-G Secret does not match StatefulSet")
    if not secret.get("data", {}).get(".walg.env"):
        raise ValueError("WAL-G configuration is missing")
    pvc_items = read_json(kube + ["get", "pvc", "-o", "json"])["items"]
    pvcs = select_pvcs(pvc_items, release, ns, cluster)
    pods = read_json(kube + ["get", "pods", "-o", "json"])["items"]
    owned_pods, primaries = [], []
    names = {p["metadata"]["name"] for p in pvcs}
    for pod in pods:
        labels = pod["metadata"].get("labels", {})
        is_member = all(labels.get(k) == v for k, v in selector.items())
        owners = pod["metadata"].get("ownerReferences", [])
        controlled = any(o.get("uid") == sts["metadata"]["uid"] and o.get("controller") for o in owners)
        mounted = {v.get("persistentVolumeClaim", {}).get("claimName") for v in pod["spec"].get("volumes", [])}
        if (is_member and not controlled) or (mounted & names and not (is_member and controlled)):
            raise ValueError("Ambiguous pod/PVC ownership")
        if is_member:
            if not mounted & names:
                raise ValueError("PostgreSQL pod does not mount a selected PVC")
            owned_pods.append(pod)
            if labels.get("role") == "primary" and any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod.get("status", {}).get("conditions", [])):
                primaries.append(pod)
    if len(primaries) != 1:
        raise ValueError("Recovery preflight requires exactly one readable, ready primary; offline recovery is not supported")
    primary = primaries[0]["metadata"]["name"]
    backups = read_json(kube + ["exec", primary, "-c", "patronimvp", "--", "/wal-g/wal-g", "backup-list", "--detail", "--json", "--config", "/wal-g-credentials/.walg.env"])
    backup = select_backup(backups, target, cluster, args.backup_name)
    if values[pgcat].get("patroniReleaseName") != release:
        raise ValueError("PgCat release does not reference the intended Patroni release")
    config = base64.b64decode(secret["data"][".walg.env"]).decode()
    for key in ["AWS_ENDPOINT", "WALG_S3_PREFIX", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]:
        if not re.search(rf"^{key}=.+$", config, re.M):
            raise ValueError("Incomplete WAL-G storage configuration")
    stored = {}
    for line in config.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            stored[key] = json.loads(value) if value.startswith('"') else value
    for key in ["AWS_ENDPOINT", "WALG_S3_PREFIX", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]:
        if inline and str(values[release].get("walg", {}).get(key, "")) != stored.get(key):
            raise ValueError("Live WAL-G Secret differs from saved Helm values; reconcile before recovery")
    # Inventory DCS objects before shutdown; remove only exact cluster-scoped names.
    dcs = []
    selector_text = ",".join(f"{k}={v}" for k, v in selector.items())
    for kind in ["endpoints", "configmaps"]:
        for obj in read_json(kube + ["get", kind, "-l", selector_text, "-o", "json"])["items"]:
            name = obj["metadata"]["name"]
            # The Endpoints controller copies the two validated role-Service labels.
            # These are routing objects, not Patroni DCS keys; Helm removes their Services.
            if kind == "endpoints" and name in {f"patronimvp-master-{release}", f"patronimvp-replica-{release}"}:
                continue
            if name not in {cluster, f"{cluster}-config", f"{cluster}-sync", f"{cluster}-failsafe"}:
                raise ValueError("Unexpected DCS object; manual review required")
            dcs.append((kind, name))
    return dict(namespace=ns, release=release, pgcat=pgcat, cluster=cluster, target=target,
                backup=backup, pvcs=pvcs, pods=owned_pods, values=values, dcs=dcs)


@contextmanager
def recovery_workspace(args, plan):
    """Retain sensitive recovery values only with explicit --state-dir opt-in."""
    retained = getattr(args, "state_dir", None)
    temporary = None
    if retained:
        directory = Path(retained).resolve()
        # Refuse reuse, including symlinks: each execution owns a fresh directory.
        if Path(retained).is_symlink():
            raise ValueError("State directory must not be a symlink")
        directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    else:
        temporary = tempfile.TemporaryDirectory(prefix="dbaas-recovery-")
        directory = Path(temporary.name)
    state = {"namespace": plan["namespace"], "release": plan["release"],
             "backup": plan["backup"], "stage": "prepared", "retained": bool(retained)}
    def stage(value):
        state["stage"] = value
        if value == "pvc-deletion-started":
            state["pvcDeletionStarted"] = True
        fd = os.open(directory / "state.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(state, output)
        print("RECOVERY STATE: " + value)
    stage("prepared")
    try:
        yield str(directory), stage
    except Exception:
        failed_stage = state["stage"]
        stage("failed-at-" + failed_stage)
        print("Recovery stopped at " + failed_stage + ". Partial changes may remain; do not rerun deletion blindly.", file=sys.stderr)
        if state.get("pvcDeletionStarted"):
            print("DATABASE DATA MAY ALREADY BE DELETED. There is no automatic rollback. Verify backup storage is intact, inspect remaining PVCs, and review the reinstall steps below before any further mutation.", file=sys.stderr)
        if retained:
            print("Private recovery values and state retained at " + str(directory), file=sys.stderr)
            ns = plan["namespace"]
            for name, component in [(plan["release"], "patroni"), (plan["pgcat"], "pgcat")]:
                command = ["helm", "upgrade", "--install", name, str(ROOT / "helmCharts" / component),
                           "-n", ns, "-f", str(directory / (component + ".json")),
                           "--wait", "--wait-for-jobs", "--timeout", "60m"]
                print("After inspecting surviving pods/PVCs and resolving the failure, review: " + shlex.join(command), file=sys.stderr)
        else:
            print("Temporary values will be removed. Reconstruct original chart values from your secured configuration, select the reported backup/target, then reinstall Patroni followed by PgCat. Use --state-dir on future attempts to retain exact commands and values.", file=sys.stderr)
        raise
    finally:
        if temporary:
            temporary.cleanup()


def recover(args):
    plan = preflight(args)
    ns, release, pgcat = plan["namespace"], plan["release"], plan["pgcat"]
    kube = ["kubectl", "-n", ns]
    with recovery_workspace(args, plan) as (directory, stage):
        files = {}
        plan["values"][release]["postgres"].update(BACKUP_ENABLE=True, BASE_BACKUP_NAME=plan["backup"],
                                                      RECOVERY_TARGET_TIME=plan["target"].isoformat(sep=" "))
        for name, component in [(release, "patroni"), (pgcat, "pgcat")]:
            path = Path(directory) / f"{component}.json"
            path.write_text(json.dumps(plan["values"][name]))
            path.chmod(0o600)
            files[name] = str(path)
            # Render without exposing Secret contents, before destructive actions.
            run(["helm", "template", name, str(ROOT / "helmCharts" / component), "-n", ns, "-f", str(path)])
        print(f"RECOVERY TARGET: {plan['target'].isoformat()}\nNAMESPACE: {ns}\nRELEASE: {release}\nPOSTGRES CLUSTER: {plan['cluster']}\nBASE BACKUP: {plan['backup']}\nPVCs TO DELETE:")
        for pvc in plan["pvcs"]:
            print(f"  {pvc['metadata']['name']} (uid={pvc['metadata']['uid']})")
        print("Backup metadata identified; WAL coverage and recovered data are NOT verified.")
        if not args.execute:
            print("DRY RUN: no cluster mutations performed. Use --execute only after reviewing this plan.")
            return
        # Recheck identities immediately before mutation, never delete by a broad selector.
        for pvc in plan["pvcs"]:
            current = read_json(kube + ["get", "pvc", pvc["metadata"]["name"], "-o", "json"])
            if current["metadata"]["uid"] != pvc["metadata"]["uid"]:
                raise ValueError("PVC identity changed since preflight")
            select_pvcs([current], release, ns, plan["cluster"])
        print("EXECUTING DESTRUCTIVE IN-PLACE RECOVERY")
        stage("uninstall-started")
        run(["helm", "uninstall", pgcat, "-n", ns, "--wait", "--timeout", "5m"])
        # Patroni can recreate its configuration Service while Helm removes it.
        # Stop the validated StatefulSet first so uninstall cannot race its DCS loop.
        stage("patroni-shutdown-started")
        run(kube + ["scale", "statefulset/" + plan["cluster"], "--replicas=0"])
        for pod in plan["pods"]:
            run(kube + ["wait", "--for=delete", f"pod/{pod['metadata']['name']}", "--timeout=180s"])
        stage("patroni-uninstall-started")
        run(["helm", "uninstall", release, "-n", ns, "--wait", "--timeout", "5m"])
        for pod in plan["pods"]:
            run(kube + ["wait", "--for=delete", f"pod/{pod['metadata']['name']}", "--timeout=180s"])
        stage("dcs-cleanup-started")
        for kind, name in plan["dcs"]:
            run(kube + ["delete", kind, name, "--ignore-not-found=true", "--wait=true"])
        for pvc in plan["pvcs"]:
            current = read_json(kube + ["get", "pvc", pvc["metadata"]["name"], "-o", "json"])
            if current["metadata"]["uid"] != pvc["metadata"]["uid"]:
                raise ValueError("PVC identity changed during shutdown; aborting deletion")
            select_pvcs([current], release, ns, plan["cluster"])
            stage("pvc-deletion-started")
            run(kube + ["delete", "pvc", pvc["metadata"]["name"], "--wait=true", "--timeout=180s"])
        for name, component in [(release, "patroni"), (pgcat, "pgcat")]:
            stage("install-" + component + "-started")
            run(["helm", "upgrade", "--install", name, str(ROOT / "helmCharts" / component), "-n", ns,
                 "-f", files[name], "--wait", "--wait-for-jobs", "--timeout", "10m"])
            if component == "patroni":
                replicas = plan["values"][release]["postgres"]["replicaCount"]
                run(kube + ["wait", f"--for=jsonpath={{.status.readyReplicas}}={replicas}",
                            "statefulset/" + plan["cluster"], "--timeout=600s"])
        stage("deployed-data-verification-pending")
        print("Helm recovery deployment completed. Verify target-time data and routing before declaring PITR successful.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="dbaas")
    parser.add_argument("--patroni-releasename", default="patroni-mvp")
    parser.add_argument("--pgcat-releasename", default="pgcat-mvp")
    parser.add_argument("--recovery-time", required=True, help="YYYY-MM-DD HH:MM:SS, interpreted as UTC")
    parser.add_argument("--backup-name", help="Explicit base backup; otherwise newest identifiable backup completed before target")
    parser.add_argument("--state-dir", help="Create a NEW private directory to retain values and recovery state, including after failure")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="Delete the reviewed cluster volumes and redeploy")
    mode.add_argument("--dry-run", action="store_true", help="Default; only inspect resources and render charts")
    args = parser.parse_args()
    if args.execute and not args.state_dir:
        parser.error("--execute requires --state-dir pointing to a new private directory")
    try:
        recover(args)
    except yaml.YAMLError:
        parser.exit(1, "Recovery aborted: invalid PgCat YAML configuration\n")
    except (ValueError, RuntimeError, KeyError, OSError) as exc:
        parser.exit(1, "Recovery aborted: preflight or command failed; inspect operator configuration\n")


if __name__ == "__main__":
    main()
