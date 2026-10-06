# Phase 4 runtime validation report

Execution date: 2026-10-03. All prior uncommitted Phase 1–3 work was preserved. No commit or push. This report describes experimental disposable-cluster observations, not production availability, RPO or RTO guarantees.

## Kubernetes API EOF Root Cause

The host's root-user inotify instance limit was exhausted at `fs.inotify.max_user_instances=128`. A fresh root process with only four open descriptors received errno 24 from `inotify_init1`; kube-proxy failed with `failed complete: too many open files`. CoreDNS was unready. From the API pod, TCP to the Kubernetes Service connected but CA-verified TLS failed with unexpected EOF, and Service DNS failed.

The mounted ServiceAccount token, CA and namespace were readable. `KUBECONFIG` was absent; Kubernetes Service host/port were supplied. All eight upper/lowercase proxy variables were absent in the API pod; direct tests failed too. Node Docker proxy keys were empty, not active proxies. There was no evidence that proxy interception caused this failure.

Evidence: [before](../../results/runtime/logs/api-connectivity-before.json), [after](../../results/runtime/logs/api-connectivity-after.json), [kernel diagnosis](../../results/runtime/logs/inotify-root-cause.json), [kube-proxy error](../../results/runtime/logs/kube-proxy-before.txt). This matches [kind's documented inotify exhaustion issue](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files).

## Fix

Temporarily increased the host limit to 1024 through the privileged, task-owned diagnostic kind node, then restarted only that cluster's kube-proxy. CoreDNS recovered. The same API pod passed DNS, TCP, CA-verified TLS 1.3, authenticated HTTPS 200, Helm list/template and authorization checks. All 105 required verb/resource checks passed ([RBAC evidence](../../results/runtime/logs/api-rbac.json)). Namespace GET was Forbidden as expected for this namespaced provisioner; namespace creation is an operator responsibility.

Helm uses standard in-cluster ServiceAccount credentials. No token-bearing kubeconfig was added to the API, no cluster-admin was granted, no TLS verification was disabled and no proxy settings were changed. The harness now waits for kube-proxy and CoreDNS. Host sysctl changes remain an operator action, not an automatic smoke-test side effect. Cleanup outcome is recorded below.

## Test Environment

Single-node kind, Kubernetes v1.30.0, local-path RWO storage, one primary and one asynchronous streaming replica. Two database members were chosen for this minimal smoke profile; a three-member multi-node failure profile remains Planned. Docker reported 12 CPUs and 32,881,127,424 bytes available; these are host/daemon capacity, not dedicated pod allocations. PostgreSQL 16.6 and Patroni 4.0.4 ran in the custom `dbaas/patroni:2.1.0` image. One PgCat, one MinIO and one API replica were used. pgAdmin used the chart's pinned image.

Seven local images: WAL-G 3.0.7, Patroni image 2.1.0, watcher 1.1.0, MinIO RELEASE.2025-04-22T22-12-26Z, mc RELEASE.2025-04-16T18-13-26Z, kubectl 1.30.0 and backend 0.2.0. [Environment](../../results/runtime/environment.json) identifies the final cluster. This topology cannot model node or storage failure domains.

## Provisioning Result

The real authenticated `POST /api/deploy` creates `smoke-minio`, `smoke-patroni` and `smoke-pgcat` in `dbaas-smoke`. Evidence includes the API response, release states, resource identities and Secret names only. The API now explicitly waits for StatefulSet readyReplicas because Helm's OnDelete handling did not establish pod readiness before installing dependent components. No unrelated resources are selected.

## PostgreSQL/Patroni Result

Exactly one primary and one streaming replica were observed. Membership, timelines, replication state and per-member creation-to-Ready timestamps are recorded under `results/runtime/patroni/`. Primary/replica Service endpoint IPs were compared against the intended role pods. Both members share one node: this proves replication in the lab, not platform HA.

## PgCat Result

An independent client pod authenticates to `smoke-pgcat-proxy-service:5432`, using the configured Secret. Queries reach PostgreSQL through PgCat. Backend address/recovery-state samples are stored in `sql/routing.json`; observed roles are reported with final measurements below. Writes and deterministic reads succeeded. This is a small routing check, not comprehensive SQL-parser or transaction-mode coverage. Secret hot reload remains untested.

## SQL Result

`validation_test` holds deterministic id/phase/value rows. The harness compares the complete expected dataset through PgCat, directly on the primary and read-only on the replica. Separate unique-ID continuous writes track acknowledged commits during failures. Expected baseline/final datasets are retained. Failed/time-out probes may have committed; they are not classified as acknowledged.

## Backup Result

The harness creates a Job from the chart's intended backup CronJob. It requires Job completion, WAL-G backup-list metadata and actual MinIO backup objects, including a stop sentinel. Logs, backup identifier, sizes, timestamps and object keys are retained under `backup/`. It does not substitute a direct backup-push command for the platform path. A further backup runs during writes; that second backup is not separately restored.

## WAL Archiving Result

After the base backup, a new row is written and WAL is switched. The harness requires pg_stat_archiver progression and the corresponding WAL segment object in MinIO. `backup/wal.json` captures both observations. This does not prove archive retention or arbitrary historical WAL coverage.

## PITR Result

The destructive flow remains opt-in with `RUN_PITR_TEST=1`. The real operator recovery CLI selects a base backup completed before UTC target T, validates ownership and PVC identities, stops workloads, cleans reviewed DCS objects, deletes only reviewed claims and reinstalls. The harness verifies row A survives, row B written after T is absent, and new row C is writable and replicated. Exact timestamps and outcomes are recorded under `pitr/`.

A diagnostic recovery passed, but the next clean attempt exposed an uninstall race: Patroni recreated its configuration Service after Helm deleted it. Helm timed out before PVC deletion. The surviving Service creation timestamp and labels are retained in [race evidence](../../results/runtime/logs/recovery-service-recreation.json). Recovery now scales the validated StatefulSet to zero and waits for its pods to disappear before uninstalling its Services. The next clean rerun passed PITR in 68.532 seconds, then exposed a failure-test limitation: immediate primary replacement could reacquire leadership before replica promotion. That attempt correctly failed the promotion assertion. The final profile temporarily cordons only its disposable node during primary deletion, leaving the existing replica/client running, and uncordons after promotion or on failure. It tests a sustained primary outage; it is not a node-drain experiment. Archived attempts retain their individual outcomes; the diagnostic success is not substituted for final-run results.

## Primary Failover Result

The current primary pod is force-deleted while an independent client continuously writes through PgCat. Evidence records injection UTC, observed promotion, SQL availability, stable membership, timestamped Patroni events and JSON/CSV query samples. All acknowledged probe IDs and the deterministic dataset are checked, followed by a new write. Internal Patroni failure-detection time is **NOT OBSERVED separately**; polling the new primary is an upper-bound promotion observation, not an internal detection measurement.

## Replica Failure Result

One replica is force-deleted. The harness checks that the original primary remains primary, writes continue, the replica rejoins and expected data catches up. Sampling results and rejoin observations are retained. No-failure samples do not establish a zero-duration interruption.

## PgCat Failure Result

The final profile force-deletes the single proxy pod and measures client failures/recovery using a separate client pod. The earlier diagnostic attempt used a rolling replacement and is labelled separately. Each query opens a fresh connection; application reconnect/retry behavior for persistent sessions is not validated. A single PgCat replica remains an SPOF.

## Network Policy Result

**NOT APPLICABLE** to this live profile: default kind CNI does not enforce NetworkPolicy, so optional policies remain disabled. Enforced allowed/denied flows and tenant isolation are **NOT VALIDATED**. Multi-worker drain/PDB/topology behavior is also **NOT APPLICABLE** here.

## Runtime Defects Found and Fixed

| Defect | Source correction and rationale |
|---|---|
| OnDelete readiness gap | API and recovery explicitly wait for expected StatefulSet readyReplicas before depending on those workloads. |
| pgAdmin rejects reserved email domain | Both chart families use `admin@example.com` as the non-secret default login email. |
| WAL-G parses `.env` as dotenv | Smoke Secret writes quoted KEY=value lines, with PostgreSQL TCP credentials, rather than JSON under an `.env` filename. |
| Transient MinIO alias startup failures | Both hook scripts use bounded, timed retries with fixed-stage logging; failed Job pods retain diagnostic status. |
| Backup primary guard assumes socket trust | Both chart scripts and health checks use authenticated loopback TCP with the existing Secret environment. HBA was not weakened. |
| Role Services add Endpoints to DCS selection | Recovery excludes only the two exact, already validated role-Service Endpoint names; unknown DCS resources still abort preflight. |
| Patroni recreates config Service during uninstall | Stop the validated StatefulSet and wait for pods before Helm removes Patroni Services. Shutdown failure stops before volume deletion. An additional preflight rejects automatic PVC deletion policies before scaling; that guard was added after the final live run and is regression-tested offline. The live profile used Retain/Retain. |

Regression coverage checks ordering/failure behavior, retained volume safety, DCS inventory, chart parity, dotenv format, bounded/redacted retries, API readiness and evidence status/redaction/archive behavior. Upstream WAL-G can echo malformed configuration in its errors; one raw diagnostic exposed only a generated disposable credential. That failed cluster was removed, raw output was excluded from repository evidence, and subsequent logs use known-value redaction. Operators must still restrict access to pod logs.

## Changed Files and Design Decisions

- `application/app/main.py`: explicit readiness barrier between dependent releases.
- Both `helmCharts/` families: MinIO initialization retries, PostgreSQL backup TCP authentication and pgAdmin default email; behavior remains aligned.
- `scripts/recovery.py`: exact DCS inventory, explicit shutdown and restored member readiness, while retaining ownership/PVC checks and opt-in destructive execution.
- `scripts/smoke-test/{run.py,lifecycle.py,evidence.py}`: isolated provisioning, actual SQL/backup/restore/failure checks, secret-safe machine-readable artifacts and generated summary.
- `scripts/validate/{kubernetes-api.py,health.py}`: reproducible connectivity diagnostics and real authenticated database checks.
- `tests/test_runtime.py` and existing test fixtures: runtime defect regressions without replacing prior checks.
- README, testing/security/operations guides, capability matrix and risk register: synchronized behavior and validation boundaries.
- `results/runtime/`: actual observations, sanitized logs and separate attempt archives. No screenshots or new architectural diagrams were introduced.

## Measured Timings

Final run measurements are appended below from machine-readable artifacts. Timings include command, scheduling and polling latency. They are observations on this local disposable environment, not service objectives or benchmark comparisons.

## Remaining Runtime Risks

Destructive in-place PITR still interrupts service and removes reviewed original claims; isolated restore and controlled cutover remain Planned. API operations are synchronous without durable state or per-release locking. Authentication uses a shared operator identity. Backup retention, object lock, off-site copies, credential rotation, TLS between data-plane components and production restore policy are not established. Two asynchronous database members do not promise zero data loss. Forced pod deletion on a healthy node does not model a partitioned or unreachable node.

## Remaining SPOFs

One lab node/control plane and local storage failure domain; one MinIO pod/local volume; one PgCat replica; one API replica. pgAdmin is also single-replica but is not the SQL data path. Local backups share the database's physical failure domain.

## Not Yet Tested

Three-member multi-node failover, node drain/PDB eviction, topology spreading, storage detachment/reattachment across nodes, enforcing CNI policies, cross-tenant rejection, cloud/object-store failures, remote backup restore, restore of the concurrent-write backup, WAL gaps/multiple historical timelines, long-lived client sessions, upgrades, live scaling, credential rotation, Secret reload, sustained load, observability integration, TLS/ingress, architecture portability and registry promotion. No Grafana dashboard or unavailable metric was fabricated.

Recommended Phase 5: isolated restore/cutover and off-site backup policy first, then a multi-node enforcing-CNI test profile, multiple PgCat replicas and persistent-client retry tests. Add measured observability and repeatable failure scenarios before setting any availability or recovery objectives.

## Final clean run — LIVE VALIDATED

Cluster: `dbaas-smoke-8096d8730a`; namespace: `dbaas-smoke`. All 13 applicable checks passed. Node drain and NetworkPolicy enforcement are NOT APPLICABLE in this profile. See [generated summary](../../results/runtime/summary.md) and [attempt history](../../results/runtime/attempts/README.md).

| Observation | Measured result |
|---|---|
| API provisioning | 143.205 s |
| PostgreSQL pod creation → Ready | 14.0 s (smoke-patroni-patronimvp-0), 15.0 s (smoke-patroni-patronimvp-1) |
| Post-API readiness confirmation | 0.205 s; not total bootstrap time |
| Baseline backup Job/catalog check | 3.21 s |
| PITR including data verification | 67.481 s |
| Primary failure | new primary observed at 25.171 s; SQL available observed at 25.37 s; stable database members at 37.096 s; 5 failed samples; 20 acknowledged probe writes, none missing |
| Primary failure: sampled interruption | 22.705 s from first failed query start to last failed query completion; first successful probe completion after failure at 25.369 s after injection |
| Replica failure | SQL available observed at 0.204 s; stable database members at 10.87 s; 0 failed samples; 18 acknowledged probe writes, none missing |
| PgCat force deletion | SQL available observed at 2.53 s; stable database members at 2.747 s; 3 failed samples; 3 acknowledged probe writes, none missing |
| PgCat force deletion: sampled interruption | 1.431 s from first failed query start to last failed query completion; first successful probe completion after failure at 2.579 s after injection |

PITR target: **2026-10-03 10:04:03 UTC**. Exact A/B creation timestamps are in `pitr/attempt.json`; A present/B absent/C written is recorded in `pitr/result.json`. Selected baseline backup: `base_000000010000000000000004`; 2,788,339 compressed bytes and 23,424,588 uncompressed bytes as reported by WAL-G. Object keys and archived WAL segment are retained.

PgCat routing observed 8 backend samples; primary and replica recovery-state values were both present. This demonstrates both configured read backends in this sample; broader routing semantics remain untested.

The primary test held replacement scheduling until replica promotion and then restored scheduling. The selected deterministic rows and every acknowledged probe ID survived these experiments; uncertain failed writes and untested workloads prevent a universal zero-data-loss claim. A replica test with zero failed samples is reported as sampled continuity, not zero outage. PgCat results use fresh reconnecting clients and preserve its single-replica SPOF classification.

The concurrent-write backup completed while inserts continued without reported write errors. Its separate restore remains NOT RUN. The reusable cluster health validator also passed after the lifecycle tests.

## Final validation and cleanup

- Python: **60 passed** (baseline 46 plus 14 runtime regressions).
- JavaScript: **10 passed** (six UI/watcher tests and four SQL-readiness cases).
- Helm lint: **six charts passed**, covering both chart families.
- Parsers: **43 YAML, 96 JSON, 13 Python, 13 shell, 6 JavaScript and 1 TOML** files/blocks passed. Shell checks are `bash -n`; shellcheck, yamllint, kubeconform, hadolint and mmdc were unavailable. Live API application additionally exercised the deployed Kubernetes objects.
- `npm ci --offline --cache /tmp/dbaas-npm-phase3`: **37 packages installed**, reported **0 vulnerabilities**; this is the locked cached installation result, not an independent current advisory certification.
- Gitleaks 8.24.3: **0 working-tree findings; 0 findings across 148 commits**. No claim that scanners detect every secret format.
- Docker: **seven successful local image builds**, identities retained in [image-builds.json](../../results/runtime/logs/image-builds.json).
- Final live smoke/lifecycle: **13 PASS**, **2 NOT APPLICABLE**; reusable cluster health validator PASS. Failed attempts are separately retained.
- `git diff --check` passed; local links in the nine changed documentation entry points resolved.

The original host `fs.inotify.max_user_instances=128` was restored after validation. All task-owned kind clusters and retained private kubeconfig files were removed; only the pre-existing `kind` cluster remains. No operations were performed against that existing cluster. See [cleanup evidence](../../results/runtime/logs/cleanup.json) and [validation record](../../results/runtime/logs/validation.json). No commit or push was made.
