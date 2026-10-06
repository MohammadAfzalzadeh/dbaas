# Runtime validation

Phase 4 runs the real API, charts, SQL through PgCat, CronJob-derived backups, WAL archiving, opt-in PITR and controlled pod failures in disposable kind. Results and limitations are recorded in [the report](../audit/phase4-runtime-validation-report.md) and [generated summary](../../results/runtime/summary.md). These are lab measurements, not production guarantees.

## Prerequisites and the EOF diagnosis

Node Ready is insufficient. The harness now waits for kube-proxy and CoreDNS before loading application images. In this environment, `fs.inotify.max_user_instances=128` was exhausted for root: a fresh root process with four descriptors received errno 24 from `inotify_init1`. kube-proxy crashed with `failed complete: too many open files`; DNS and the Kubernetes ClusterIP then failed. Raising that limit temporarily to 1024 allowed kube-proxy/CoreDNS and the unchanged API pod to work. See [kind's documented inotify issue](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files).

The harness does **not** change host sysctls automatically. Inspect actual usage and get operator authorization before changing shared-host limits. Record and restore the original value for temporary testing. Do not solve this failure by disabling certificate checks, granting cluster-admin, using hostNetwork or bypassing the API Service.

## In-pod diagnostics and credentials

```sh
kubectl -n YOUR_NAMESPACE exec -i deployment/dbaas-backend -- python - \
  < scripts/validate/kubernetes-api.py
```

This script checks token/CA/namespace readability without printing their contents, all upper/lowercase proxy-variable presence, DNS, TCP, TLS with the mounted CA, authenticated HTTPS, kubectl authorization, namespace access and Helm version/list/template. Namespace GET is expected to be Forbidden for the namespaced backend; the operator creates the namespace first. A Forbidden response proves a different failure from TLS EOF. Diagnostics should be stored only after reviewing their contents.

Helm and kubectl use their standard in-cluster ServiceAccount token/CA and `KUBERNETES_SERVICE_HOST/PORT`. There is no generated token-bearing kubeconfig inside the API. The private host kubeconfig belongs only to the disposable harness.

Proxy variables were absent in the API pod and direct/proxy-bypassed tests failed identically before the inotify fix. Proxy settings were not changed. If your environment injects proxies, preserve external proxy use and configure both `NO_PROXY` and `no_proxy` to include localhost, 127.0.0.1, kubernetes, kubernetes.default, kubernetes.default.svc, .svc, .cluster.local and the actual Kubernetes API Service host. Add Service/Pod CIDRs only after discovering them for that cluster; this repository does not hardcode those CIDRs into production workloads.

## Run and retain evidence

```sh
bash scripts/smoke-test/build-images.sh
SKIP_BUILD=1 RUN_PITR_TEST=1 RUN_FAILURE_TEST=1 bash scripts/smoke-test/run.sh
python3 scripts/smoke-test/evidence.py --directory results/runtime
```

Omit the two RUN flags for a non-destructive lifecycle run. `RUN_PITR_TEST=1` enables in-place restore only inside the newly created cluster. `RUN_FAILURE_TEST=1` enables forced deletion of the current primary, one replica and the single PgCat pod, followed by backup during writes. During primary failure, the harness temporarily cordons the disposable node to prevent a same-primary replacement from winning the leader lease; existing replica/client pods keep running. It uncordons after observed promotion, including on failure. This scheduling hold is not a drain test. Never run these experiments against wanted data. A node drain is not attempted on this single-node profile. NetworkPolicy stays disabled because the default kind CNI does not enforce it.

`RUNTIME_RESULTS_DIR` selects an output directory. Before a new run, previous lifecycle artifacts are moved to its `attempts/` directory; old successes cannot become evidence for a new failed run. Root-level summary/status describe the latest run. Evidence stores explicit PASS/FAIL/NOT RUN/NOT APPLICABLE, UTC timestamps, API response, resource identities, Secret **names only**, membership/replication, expected data, backup metadata/object listings, PITR target/results and per-query failure samples. Captured credential values are redacted before evidence writes. Raw Secret manifests, tokens, kubeconfigs and retained recovery values are excluded.

Normal cleanup removes only the generated cluster. `KEEP_FAILED_CLUSTER=1` explicitly retains a failed task-owned cluster for diagnosis and writes its kubeconfig under `/tmp/<generated-name>.kubeconfig` with mode 0600. Inspect it, delete only that exact cluster, then remove the private kubeconfig. Retention is off by default. The harness never reuses an existing cluster. Run one harness at a time per results directory, or choose distinct `RUNTIME_RESULTS_DIR` paths. Harness temporary recovery values are removed on exit even when retaining a failed cluster; use the standalone recovery CLI with its own private `--state-dir` when operator recovery state must survive.

## What the measurements mean

Provisioning duration wraps the authenticated HTTP call, including chart waits. Per-member readiness uses Kubernetes creation/Ready timestamps; the separate post-API readiness check is only a confirmation duration. Backup duration includes Job creation, completion and WAL-G listing. PITR duration includes destructive shutdown/recreation and data assertions.

A separate client pod connects to the PgCat Service. It uses a new authenticated connection per query; it does not model long-lived sessions. Failure probes insert unique IDs before/during/after disruption, record success/failure and latency, then verify all acknowledged IDs against the database. Timed-out writes may have committed: they are not counted as acknowledged. The selected deterministic dataset is checked through PgCat, on the primary and on replicas after recovery. This verifies those test rows, not universal zero data loss.

Promotion is observed by polling the primary role. Internal Patroni detection time is not inferred from that observation. Selected timestamped Patroni events are retained when available. Sampling/polling and query timeouts bound the observed interruption; zero failed samples is not a zero-outage guarantee. The diagnostic attempt used a rolling PgCat replacement; the final run uses single-pod deletion and identifies its target explicitly.

Backup during writes verifies Job completion, remote backup metadata and continuing successful writes. The separate PITR test restores the baseline backup; restoring the concurrent-write backup is not yet tested.
