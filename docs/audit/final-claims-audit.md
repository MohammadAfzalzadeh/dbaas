# Final claims audit

Review date: 2026-10-04. This register extracts substantive prose claim units from all requested public-facing documents. Multi-sentence paragraphs stay together where their caveats define the claim. Headings, standalone asset links and publishing instructions are omitted. Tables in README are assessed separately below. Exact quotes refer to the corrected candidate; confirmed earlier inconsistencies are recorded in the corrections section.

**SUPPORTED** means support at the scope stated, not production certification. **PARTIALLY SUPPORTED** identifies missing evidence or a stronger interpretation that needs qualification. **OUTDATED** identifies wording overtaken by repository state. No unsupported numeric result was discovered: raw arithmetic matched. Unsupported production/zero-RPO interpretations are explicitly rejected, rather than attributed as quotations the documents never made.

Common evidence: [source inventory](../../results/validation/phase6-5/document-inventory.json), [measurement audit](../../results/validation/phase6-5/measurement-audit.json), [final review](final-independent-review.md). Historical measurements are corroborated by raw artifacts, not by treating the prior prose as authority.

## README.md

### C001 — SUPPORTED

```text
A PostgreSQL DBaaS prototype built with **FastAPI, Helm, Kubernetes, Patroni, PgCat, WAL-G and MinIO**. It provisions database stacks through an authenticated browser/API workflow and records how they behave under controlled failures. The disposable lab demonstrated isolated recovery that survives restart and three automatic node-loss recovery reruns; an earlier replica-recovery failure remains unresolved. [Evidence](docs/evidence/README.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C002 — SUPPORTED

```text
This research and platform-engineering project connects a provisioning control plane to a PostgreSQL data plane. It includes implementation, failure investigations, reproducible test tools and measured results. It is not presented as a production managed service.
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C003 — SUPPORTED

```text
Browser/UI → FastAPI → Helm/Kubernetes → Patroni/PostgreSQL, with PgCat as the SQL connection layer and WAL-G/object storage as the recovery path. The API provisions named releases and uses existing Secret references. Durable asynchronous operations, tenant identity and continuous reconciliation remain future work.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C004 — SUPPORTED

```text
Validation labels apply to individual experiments. [Claims register](docs/evidence/claims-register.md) · [Project status](docs/evidence/project-status.md).
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C005 — SUPPORTED

```text
FastAPI authenticates the operator, checks the namespace allowlist, validates inputs, renders private values files, lints selected charts, then deploys dependencies sequentially. Failure responses identify completed releases; no automatic rollback is promised. [API flow](docs/diagrams/provisioning-flow.mmd) · [Application guide](application/README.md).
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C006 — SUPPORTED

```text
Patroni manages PostgreSQL leadership through Kubernetes DCS and asynchronous replication. StatefulSets supply identity and storage, not database leader election. The tested resilience profile spreads members across workers, but those workers share one host. PDBs govern voluntary eviction; they do not protect against every abrupt failure. [HA evidence](docs/evidence/README.md).
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C007 — SUPPORTED

```text
PgCat routes connections through primary/replica Services. Independent watchers atomically generate TOML from a projected Secret. The lab tested two proxies; the chart default is one. A Service can route new connections to a survivor, but an established session can disconnect. The final benchmark uses transaction pooling; the historical default is session pooling. [Connection diagram](docs/diagrams/pgcat-routing.mmd) · [Failure report](docs/report/failure-engineering.md).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C008 — SUPPORTED

```text
A scoped CronJob-derived Job selects the primary, verifies its role, and executes WAL-G. WAL archival is checked against database state and object keys. MinIO is a local development target, not an independent disaster-recovery site. [Backup path](docs/diagrams/backup-wal-path.mmd).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C009 — SUPPORTED

```text
Recovery selects a backup completed before an explicit UTC target and replays archived WAL; the validation harness checks rows around that target. Backup success alone is not restore proof. The in-place workflow is explicitly destructive. Its guards reject invalid/future targets and ownership mismatches, but do not prove complete WAL coverage before deletion; rehearse on an isolated target first. Its measurements belong to a separate experiment. [Recovery operations](docs/operations/restore-cutover.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C010 — SUPPORTED

```text
The preferred rehearsal creates a new release and new PVCs. After promotion, automatic source archive reads and writes are disabled. Tests retained recovered A and new clone C, excluded post-target B and future source D, and proved writability after graceful and abrupt replacement. Cutover remains an operator decision. [Durability evidence](results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C011 — PARTIALLY SUPPORTED

```text
Shared Bearer authentication, namespace allowlisting, namespaced RBAC and existing Secrets form the operator boundary. Values files are private and temporary; logs and evidence are redacted. This does not provide tenant identity, comprehensive TLS or a complete credential-rotation service. [Security model](docs/security/security-model.md).
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).
- **Recommended wording:** Describe a trusted operator boundary and tested application login reload, not comprehensive tenant security or rotation.

### C012 — SUPPORTED

```text
The resilience lab used one control-plane container, three workers, three database members and two proxies. Local-path volumes stay tied to their node. All task-owned labs were cleaned up after validation. [Topology](docs/images/architecture/multinode-topology.svg) · [Environment and cleanup evidence](docs/evidence/README.md).
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C013 — SUPPORTED

```text
Calico allow/deny probes exercised SQL, replication, object storage and Kubernetes API flows. Unrelated clients and cross-release source SQL access were denied in the tested profile. This is not a complete multi-tenancy proof. [Trust boundaries](docs/images/architecture/network-boundaries.svg).
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C014 — SUPPORTED

```text
Prometheus Operator, ServiceMonitors and Grafana use actual Patroni, PgCat, MinIO and Kubernetes metrics. **Seven targets refused connections:** controller-manager, etcd, scheduler and four kube-proxy endpoints. SQL-exporter metrics, API operation metrics, backup-age instrumentation and log delivery remain incomplete. [Exact targets and observed errors](docs/report/observability-gaps.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C015 — SUPPORTED

```text
The final matrix contains 24 completed, ten-second pgbench samples at concurrency 1/10/25/50 across direct/PgCat routes and three profiles. At ten mixed clients: direct **1,401 TPS**, PgCat **1,158 TPS**. No failed transactions were reported in completed samples; percentiles and reconnect counts were not reported. [Full measured matrix](docs/report/performance-results.md).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C016 — SUPPORTED

```text
The paired sample measured **1,232 TPS baseline** and **1,153 TPS during backup**, a **6.40% decrease** calculated from raw values by the reporting script. The samples are too short to establish a general backup overhead. [Calculation and evidence](docs/report/performance-results.md#backup-impact).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C017 — SUPPORTED

```text
The **113.8 MiB** and **500.7 MiB** payloads restored and passed writable/data checks in **15.181 s** and **16.499 s**. Payloads are compressible; timings include scheduling and checks, not replay alone. [Measured recovery results](docs/report/performance-results.md#restore-and-pitr-measurements).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C018 — SUPPORTED

```text
- **UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS:** one source replica required manual reinitialization. It is not classified as fixed.
- Shared host, local volumes and a single MinIO constrain failure domains; chart defaults are not the full resilience profile.
- Seven broken scrape targets and incomplete instrumentation; a scrape-fault alert attempt also failed its observation bound.
- External/off-site recovery, replication credential rotation and notification delivery remain **NOT VALIDATED**.
- No production capacity, RPO, RTO or SLA is established. [Production gap analysis](docs/report/production-gap-analysis.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C019 — SUPPORTED

```text
Start with local checks; these commands do not deploy a cluster. Install Python 3.11 or later, Node/npm and Helm, then run from the repository root:
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C020 — SUPPORTED

```text
```bash
python3 -m venv .venv
.venv/bin/pip install -r application/app/requirements.txt -r scripts/requirements.txt
npm ci --prefix pgcat
.venv/bin/python -m unittest discover -s tests
node tests/test_ui.js
node tests/test_pgcat_health.js
.venv/bin/python tests/validate_static.py
```
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C021 — SUPPORTED

```text
With Docker available, build the project images using `bash scripts/smoke-test/build-images.sh`. For actual provisioning, follow the [owned-lab guide](docs/testing/resilience-validation.md) or [application guide](application/README.md), including Secret contracts, explicit context selection and cleanup. Do not use `init.bash` as a harmless verification command: it recreates a named kind cluster.
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C022 — SUPPORTED

```text
The [authoritative index](docs/evidence/README.md), [claims register](docs/evidence/claims-register.md) and [final validation summary](docs/evidence/final-validation-summary.md) define what may be claimed. Historical failed attempts remain separate from successful reruns.
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C023 — SUPPORTED

```text
Measure client recovery separately from leader promotion. Validate restores rather than trusting successful backup commands. Keep restored clusters independent from source archives. Diagnose each container during slow shutdown. Preserve unresolved failures instead of converting successful retries into a root-cause claim.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

## docs/report/executive-summary.md

### C024 — SUPPORTED

```text
This project implements a PostgreSQL Database-as-a-Service prototype on Kubernetes. A browser interface calls an authenticated FastAPI control plane, which validates operator inputs and deploys Helm releases. Patroni manages PostgreSQL replication and leadership. PgCat supplies connection pooling and routing. WAL-G writes base backups and archived WAL to an S3-compatible destination; the validated lab uses MinIO.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C025 — SUPPORTED

```text
The engineering objective was to make an existing research repository understandable, repeatable and testable under failure. A successful deployment is only the starting point. The project asks whether clients can use the service, whether backups restore the intended data, what happens during maintenance and abrupt loss, and which observations justify a public claim. The resulting package includes implementation, regression checks, raw runtime artifacts, measured charts and an explicit record of unresolved failures.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C026 — SUPPORTED

```text
The [evidence index](../evidence/README.md) is the authority for validation scope. The [engineering report](engineering-report.md) explains the implementation, and the [failure report](failure-engineering.md) records successful and unsuccessful experiments together. This is a technically evaluated prototype; it carries no availability, capacity or recovery guarantee.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C027 — SUPPORTED

```text
The control plane authenticates an operator token, restricts namespaces, validates requested configuration and invokes Helm. It checks charts before mutation and waits for resource readiness. Credentials normally arrive through existing Kubernetes Secrets. Temporary Helm values are held in private files, previews are redacted and partial completion is reported. This makes the workflow usable and inspectable, but it remains synchronous orchestration. Durable jobs, provisioning locks and continuous reconciliation are future work.
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C028 — SUPPORTED

```text
The measured multi-node profile used three PostgreSQL members and two PgCat replicas across three workers. Every kind node was a container on the same Docker host. Database volumes used local-path storage and remained attached to their original worker. These choices allowed controlled node-container failures and placement tests while imposing an important boundary: the experiment does not demonstrate independent host, disk or availability-zone resilience. [Environment](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/environment.json).
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C029 — SUPPORTED

```text
Patroni coordinates database roles through Kubernetes. StatefulSets preserve pod identity and storage relationships; they do not elect a PostgreSQL leader. PgCat gives clients a stable connection layer, but an existing TCP session can still fail when its proxy or backend disappears. Asynchronous replication means successful acknowledgement retention in an experiment cannot establish zero RPO.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C030 — SUPPORTED

```text
Authenticated provisioning produced a usable database service. SQL checks observed replication and role-aware routing. Calico allowed required traffic and denied unrelated and cross-release probes in the tested policy profile. Official backup Jobs produced WAL-G metadata and objects, and switched WAL segments appeared in object storage. Recovery checks asserted actual row state rather than relying on a successful command exit. [Capability register](../evidence/README.md#capability-register).
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C031 — SUPPORTED

```text
Target-time recovery retained a before-target row, excluded a later row and accepted a new write. Isolated restore used a separate release and PVC identities while preserving source identities. After correcting archive separation, the clone retained recovered and newly written data across both graceful and abrupt replacement. The clone was a single-member recovery target; this was not an off-site disaster-recovery drill. [Durability evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C032 — PARTIALLY SUPPORTED

```text
Application credential rotation was tested through database and proxy reload behavior: new credentials worked, old credentials failed on new connections and held sessions continued. This distinguishes login rotation from revocation of established sessions. Replication, administrative and object-store credential rotation are outside that result. [Rotation evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/rotation-reload/attempt-1/result.json).
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).
- **Recommended wording:** New credentials succeeded and old-credential connection attempts failed; old failures were not classified by SQLSTATE. Existing sessions continued.

### C033 — SUPPORTED

```text
Provisioning completed in **171.647 seconds** in the continuation lab. The duration includes this environment's deployment path and is not a provisioning SLA. [Provisioning result](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/provisioning.json).
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C034 — SUPPORTED

```text
During the four-client abrupt-loss experiment, promotion was observed at **24.378 seconds** and an independent SQL probe succeeded at **24.554 seconds**. The clients acknowledged **20,624 writes**, recorded **34 failed transactions** and **19 reconnects**, and had no acknowledged IDs missing afterward. Failed operations were not blindly replayed. Client recovery and full member convergence remained separate milestones. [Failover windows](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json).
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C035 — SUPPORTED

```text
The final benchmark contains **24 completed samples** across direct/PgCat routes, read-heavy/write-heavy/mixed profiles and several concurrency settings. Each point is one short sample on a small dataset. For mixed traffic at ten clients, direct PostgreSQL observed **1401.014 TPS**, compared with **1158.075 TPS** through PgCat. The result does not support a claim that adding a proxy makes this workload faster. [Performance report and raw-source links](performance-results.md).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C036 — SUPPORTED

```text
A paired workload measured **1231.640 TPS** without backup and **1152.865 TPS** during backup: a reporting-script calculation gives **6.40% lower TPS**. Shared resources and short sampling prevent treating that difference as an isolated causal cost. Two compressible payload relations, **113.8 MiB** and **500.7 MiB**, restored and passed writable/data checks in **15.181** and **16.499 seconds**. The durations include bootstrap and assertions, not replay alone. [Backup and recovery measurements](performance-results.md#backup-impact).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C037 — SUPPORTED

```text
A Kubernetes API EOF problem initially resembled an access or certificate issue. Diagnostics instead found host inotify exhaustion, failed kube-proxy initialization and unhealthy DNS. A temporary host-limit adjustment and restart of owned components restored CA-verified access. The solution did not require disabling TLS verification or broadening the application to cluster administrator. [Runtime diagnosis](../audit/phase4-runtime-validation-report.md#kubernetes-api-eof-root-cause).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C038 — SUPPORTED

```text
Static review found a backup false-success risk: selector and command-error handling could allow an invalid operation to appear successful. Strict selection, authenticated role checks and propagated failures corrected that path. Restore experiments exposed a separate archive-isolation risk: a writable clone must not continue following divergent source WAL after bootstrap. Proxy termination tests showed that the watcher could keep a pod alive after PgCat exited; bounded signal handling corrected the watcher behavior while preserving proxy drain time. An alert expression also required correction because Patroni's primary-role metric stayed true when PostgreSQL was stopped. [Defects and regression evidence](failure-engineering.md#development-defects-and-regression-evidence).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C039 — SUPPORTED

```text
One historical replica recovery failure remains open. The initial abrupt-loss run restored a writable primary but left a replica stuck in archive recovery until manual reinitialization. Three later clean runs recovered automatically, yet the exact earlier trigger remains unknown. Its classification is **UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS**. Successful reruns do not justify calling it fixed. [Anomaly record](failure-engineering.md#the-unresolved-replica-recovery-anomaly).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C040 — SUPPORTED

```text
Seven scrape targets refused connections in the final inventory. Actual dashboards cover available component metrics, but SQL/API instrumentation and recovery-chain visibility remain incomplete. Availability and backup alert transitions have live evidence; notification delivery does not. A later scrape-fault alert attempt failed, and subsequent harness hardening has static tests only. [Exact monitoring gaps](observability-gaps.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C041 — SUPPORTED

```text
Production deployment would require independent storage/failure domains, verified off-site restore, defined recovery objectives, trusted transport and identity boundaries, durable control-plane operations, supported upgrade procedures and representative repeated testing. Multi-tenancy would add authorization, quotas and ownership controls beyond a namespace allowlist. These are explicit deployment gates, not capabilities inferred from the project title. [Production gap analysis](production-gap-analysis.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C042 — SUPPORTED

```text
The strongest portfolio story is the engineering process: build a usable service, test its failure boundaries, identify defects with concrete observations, retain contradictory evidence and communicate what remains unknown. The repository supports that story without turning limited lab observations into production promises.
```

- **Expected evidence:** Clean installation/builds, committed file inventory and source/export correspondence.
- **Found:** Clean working candidate builds; current HEAD lacks most candidate files; cached builds are not bit-reproducible. [Artifact](../../results/validation/phase6-5/clean-builds.txt).

## docs/report/engineering-report.md

### C043 — SUPPORTED

```text
This repository implements a Cloud-Native PostgreSQL DBaaS prototype: FastAPI and Helm provision a Patroni/PostgreSQL data plane with PgCat, WAL-G and MinIO. Controlled lab experiments validate provisioning, SQL, backup, target-time recovery and selected failure behavior. The package preserves failures and distinguishes lab measurements from production guarantees.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C044 — SUPPORTED

```text
Deploying a PostgreSQL pod does not establish a database service. Operators need repeatable provisioning, usable connection endpoints, role-aware recovery, recoverable backups and evidence of what clients experience during faults. This project turns an existing Kubernetes/PostgreSQL research repository into an inspectable DBaaS prototype without replacing its working chart interfaces.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C045 — SUPPORTED

```text
Preserve existing deployments, correct configuration and backup failure paths, constrain privileged operations, test recovery against deterministic data, and retain unsuccessful experiments. The final package prioritizes traceable claims over impressive but unsupported availability language. [Claims register](../evidence/claims-register.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C046 — SUPPORTED

```text
The lab requires Kubernetes, a working container runtime, persistent volumes, reachable image sources and a CNI that enforces NetworkPolicy for policy experiments. Local validation requires Helm, Python with the pinned application/script dependencies, and Node/npm. Image builds require Docker. Browser rendering is separate from runtime deployment. [Quick start](../../README.md#quick-start), [application configuration](../../application/README.md), [reporting tools](../../tools/reporting/README.md).
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C047 — SUPPORTED

```text
A healthy API process must not be confused with authenticated Kubernetes access. The application readiness endpoint checks local prerequisites; cluster reachability has a separate diagnostic path.
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C048 — SUPPORTED

```text
The control plane is an operator-facing provisioning service. It is not a continuously reconciling Operator. The data plane can continue serving when the API is unavailable, but new provisioning depends on the API and Kubernetes control plane.
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C049 — SUPPORTED

```text
The API checks a shared Bearer token, namespace allowlist and request schema before creating releases. It lints selected charts first, then deploys dependencies in order and waits for StatefulSet readiness. Failure responses identify completed releases without claiming rollback. Private temporary directories and restrictive value-file permissions limit credential exposure during Helm execution.
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C050 — SUPPORTED

```text
Concurrent requests, API restarts and partially completed operations still need durable coordination. There is no tenant authorization or durable operation store. [API lifecycle and routes](../../application/README.md), [implementation](../../application/app/main.py), [provisioning observation](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/provisioning.json).
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C051 — SUPPORTED

```text
Helm renders StatefulSets, Services, Secrets references, ConfigMaps, backup CronJobs, RBAC, optional NetworkPolicies and disruption controls. Role Services select Patroni-managed database roles. PgCat has per-pod generated configuration state. The standalone and API chart families stay in their established paths for compatibility; both are checked during validation. [Repository map](../audit/repository-map.md).
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C052 — SUPPORTED

```text
Persistent volume identity is a recovery boundary. Helpers check release/namespace/resource ownership before destructive actions; replacing a pod is different from deleting its PVC. [Storage lifecycle source](../diagrams/storage-lifecycle.mmd).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C053 — SUPPORTED

```text
Patroni starts and manages PostgreSQL, replication and role state using Kubernetes as its DCS. The continuation baseline observed one primary and two streaming replicas. Replication is asynchronous, so a promoted replica may lack recent primary commits under other fault timings. [Baseline](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/baseline.json).
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C054 — SUPPORTED

```text
Database role, process health, streaming state and SQL assertions are separate signals. A primary-role metric can remain true when PostgreSQL is stopped; monitoring now checks process-running state too.
```

- **Expected evidence:** Recorded targets, queries and alert transitions.
- **Found:** Historical metrics/alerts have scoped evidence; seven scrape targets broken and delivery unvalidated; no fresh monitoring deployment in this review. [Artifact](../../results/validation/phase6-5/document-inventory.json).

### C055 — SUPPORTED

```text
Patroni coordinates leadership through Kubernetes DCS state. Eligibility, leadership timing and database state affect promotion. Services follow role labels; clients and pools then need usable connections to the promoted backend. A StatefulSet supplies identity and placement, not PostgreSQL leader election.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C056 — SUPPORTED

```text
Promotion, first successful independent SQL probe, persistent-client acknowledgement and complete member convergence are reported separately. The lab does not prove every network partition or fencing scenario. The initial stuck replica remains **UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS**, despite three later automatic recoveries. [Failure register](failure-engineering.md#the-unresolved-replica-recovery-anomaly).
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C057 — SUPPORTED

```text
PgCat pools connections and routes to role-aware database Services. Each pod has an independent watcher that validates and atomically replaces generated configuration. Multiple proxy endpoints help new connections survive a proxy replacement; they do not migrate an existing TCP session.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C058 — SUPPORTED

```text
An early session-pooling benchmark began on a replica and later attempted an update. The final mixed-workload profile uses transaction pooling; historical defaults remain compatible. That choice needs application compatibility testing for session state. The measured direct path was faster in the final matrix; pooling is not presented as a throughput improvement. [Performance results](performance-results.md).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C059 — SUPPORTED

```text
The official backup CronJob selects exactly one primary, authenticates the role check and propagates failures. WAL-G writes a base backup and catalog metadata to the configured object store. PostgreSQL archival supplies the WAL needed between base backup and recovery target.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C060 — SUPPORTED

```text
The harness checks Job completion, backup metadata, object keys and a switched WAL segment alongside archiver state. These observations verify the tested archive path; they do not prove every possible recovery target has a complete chain. MinIO shares the lab host failure domain. [Backup evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/backup/baseline.json), [WAL evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/backup/wal.json).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C061 — SUPPORTED

```text
Recovery selects a base backup completed before an explicit UTC target, restores files and replays archived WAL to that boundary before promotion. Deterministic markers establish a meaningful assertion: before-target data must exist, later data must be absent and a new write must succeed.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C062 — SUPPORTED

```text
The in-place workflow changes the source and requires explicit execution after plan review. The earlier single-node test is separate from later isolated restores. [In-place PITR evidence](../../results/runtime/pitr/result.json), [PITR source](../diagrams/pitr.mmd).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C063 — SUPPORTED

```text
The isolated helper creates a new release with separate PVC identities, rejects an existing target and preserves source identities. Bootstrap reads the source backup/WAL; after promotion the clone disables later source archive reads, archive writes and scheduled backups. Mounted credentials remain an access risk until separately revoked or narrowed.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C064 — SUPPORTED

```text
The corrected clone retained recovered and newly written rows across graceful and abrupt replacement while excluding source-only later data. This establishes the tested single-member clone behavior, not independent off-site recovery. Cutover remains an explicit operator decision with a write boundary and rollback plan. [Durability evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json), [cutover diagram](../diagrams/restore-cutover.mmd).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C065 — SUPPORTED

```text
The implemented boundary uses operator-token authentication, namespace allowlisting, namespaced RBAC, existing Secret references by default, private temporary values and redacted previews. Inline secrets require an explicit opt-in. NetworkPolicy limits selected traffic in the enforcing lab profile.
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C066 — SUPPORTED

```text
A shared operator token is not per-tenant identity. Kubernetes Secrets alone do not prove encryption at rest, and admission webhook TLS does not establish end-to-end SQL/API transport protection. [Security documentation](../security/), [final scan scope](../evidence/final-validation-summary.md), [production gates](production-gap-analysis.md).
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C067 — SUPPORTED

```text
Readiness/startup probes, resource configuration, graceful termination, PDBs and scheduling controls are implemented and tested at different levels. A PDB constrains voluntary eviction; it cannot stop an abrupt node loss. The watcher fix bounds its own shutdown while retaining time for PgCat to drain clients. [Reliability audit](../audit/phase3-reliability-report.md), [shutdown evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/proxy-shutdown/attempt-2/result.json).
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C068 — SUPPORTED

```text
The measured HA profile spreads three database members and two proxies over three workers. All workers and the control plane are containers on one physical host. Local-path PVCs remain tied to their worker, so a drained member cannot transparently move its data to another worker. [Topology](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/initial-topology.json), [drain observation](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/drain-replica.json).
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C069 — SUPPORTED

```text
This tests scheduling and node-container disruption, not independent rack, host, zone or storage failure. Chart defaults are smaller than the measured HA profile.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C070 — SUPPORTED

```text
Calico enforced the tested NetworkPolicies. Required SQL, replication, backup and API paths were allowed, while unrelated and cross-release database probes were denied. The default single-node CNI did not establish this boundary; enforcement evidence belongs to the multi-node profile. [Policy tests](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/network-policy.json).
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C071 — SUPPORTED

```text
Policy depends on namespaces, labels and CNI behavior. It is not sufficient proof of tenant authorization or complete egress isolation. [Trust-boundary diagram](../diagrams/network-boundaries.mmd).
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C072 — SUPPORTED

```text
The final inventory supports five dashboards and thirteen query expressions using actual component metrics. Seven scrape targets refused connections; exact endpoints and missing instrumentation are in [observability gaps](observability-gaps.md). [Inventory](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/observability-inventory.json).
```

- **Expected evidence:** Recorded targets, queries and alert transitions.
- **Found:** Historical metrics/alerts have scoped evidence; seven scrape targets broken and delivery unvalidated; no fresh monitoring deployment in this review. [Artifact](../../results/validation/phase6-5/document-inventory.json).

### C073 — SUPPORTED

```text
Availability and backup conditions completed live transitions across distinct attempts. Initial alert logic missed a stopped database because a role metric remained true; the expression now combines role and running state. Notification delivery remains NOT VALIDATED. A later scrape-fault alert attempt failed; harness hardening afterward has static regression coverage only. [Failure report](failure-engineering.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C074 — SUPPORTED

```text
Validation separates static, build, smoke, live and measured evidence. Unit tests exercise input boundaries and failure handling; chart lint/render checks examine manifests; image builds check recipes; live harnesses observe owned clusters. Failure attempts are append-only and retained separately from successful reruns.
```

- **Expected evidence:** Clean installation/builds, committed file inventory and source/export correspondence.
- **Found:** Clean working candidate builds; current HEAD lacks most candidate files; cached builds are not bit-reproducible. [Artifact](../../results/validation/phase6-5/clean-builds.txt).

### C075 — SUPPORTED

```text
Client acknowledgement sets, role checks, object metadata and restored rows provide complementary observations. Current Phase 6 checks do not refresh the historical live classification. [Final validation summary](../evidence/final-validation-summary.md), [test architecture](../diagrams/validation-architecture.mmd).
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C076 — SUPPORTED

```text
Experiments include database/proxy deletion, voluntary node drains, abrupt worker loss, target-time restore, clone restarts, credential rotation, backup under writes, policy probes and alert fault injection. Expected behavior, observed impact, known cause and final classification appear together in the [failure engineering report](failure-engineering.md).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C077 — SUPPORTED

```text
The original abrupt-loss run restored a writable primary but failed full automatic member convergence. Later successful reruns are independent observations, not a replacement for that failure.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C078 — SUPPORTED

```text
Clients record unique IDs after commit acknowledgement and verify those IDs after recovery. Failed operations remain uncertain and are not automatically replayed. In the continuation load run, four clients acknowledged 20,624 writes, with 34 failed transactions, 19 reconnects and no acknowledged IDs missing. [Raw windows](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json).
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C079 — SUPPORTED

```text
The test's timeout/reconnect behavior is part of the experiment. A new SQL probe can succeed before held clients recover; the after-probe window still included errors. This prevents confusing database promotion with complete application recovery.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C080 — SUPPORTED

```text
The continuation changed an application role password and PgCat Secret, waited for projection/reload, and checked new and old credentials against the primary and each proxy. Held direct and proxy sessions continued; no database restart was requested and proxy pod identities stayed unchanged. [Rotation evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/rotation-reload/attempt-1/result.json).
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C081 — SUPPORTED

```text
Changing login credentials does not revoke established sessions. Replication, superuser and object-store credential rotation remain NOT VALIDATED. [Rotation diagram](../diagrams/credential-rotation.mmd).
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C082 — SUPPORTED

```text
The final matrix has 24 samples: direct and PgCat routes, three workload profiles, and concurrency 1/10/25/50. Each point is one ten-second scale-1 pgbench sample. Logical balances are reset, caches are not. The final mixed profile uses transaction pooling. [Raw matrix](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/pgbench.json).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C083 — SUPPORTED

```text
Shared CPU/storage, run order, small dataset and lack of repeated samples limit inference. Mean latency is measured; percentiles and reconnect counts not emitted by this matrix remain null. Aborted session-pooling samples are preserved but excluded from completed-sample charts.
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C084 — SUPPORTED

```text
The [canonical performance report](performance-results.md) contains the full matrix and generated charts. For mixed traffic at ten clients, direct PostgreSQL observed 1401.014 TPS and PgCat 1158.075 TPS. Those observations support a comparison in this lab, not a universal ranking or production capacity claim. [Raw matrix](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/pgbench.json).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C085 — SUPPORTED

```text
The paired workload observed 1231.640 TPS at baseline and 1152.865 TPS during backup, a script-calculated relative change of −6.40%. Mean latency rose from 8.119 to 8.674 ms. [Raw backup sample](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/backup-impact.json), [calculated summary](../../results/validation/phase6/measured-summary.json).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C086 — SUPPORTED

```text
Recorded resource counters provide context; the short shared-host pair does not isolate a causal backup tax or confidence interval. [Chart and methodology](performance-results.md#backup-impact).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C087 — SUPPORTED

```text
Payload relations of 113.8 and 500.7 MiB restored and passed writable/data checks in 15.181 and 16.499 seconds respectively. The payload compresses well; timings include scheduling, bootstrap and assertions, and do not isolate replay. [Smaller sample](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/restore-size/attempt-1/result.json), [larger sample](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/restore-size/attempt-2/result.json).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C088 — SUPPORTED

```text
These points do not establish a scaling curve or external recovery time. WAL intervals include forced switches and exclude payload-generation WAL. [Complete measurement semantics](performance-results.md#restore-and-pitr-measurements).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C089 — SUPPORTED

```text
The [development defect register](failure-engineering.md#development-defects-and-regression-evidence) records **Symptom, Root cause, Fix, Regression test and Final status** for Kubernetes API EOF/inotify exhaustion, backup false-success risk, namespace/RBAC errors, PgCat naming/configuration, clone archive coupling, watcher shutdown and alert logic.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C090 — SUPPORTED

```text
The replica recovery anomaly has an explicitly unknown root cause. Three later successful clean runs did not establish a fix. The scrape-fault attempt remains FAILED after static harness improvements. These are retained as first-class engineering outcomes rather than hidden in a successful aggregate.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C091 — SUPPORTED

```text
[Production gaps](production-gap-analysis.md) separates critical gates, high-priority engineering, medium-priority operational work and optional product features. Independent storage failure domains, off-site restore, trustworthy transport/identity and agreed recovery objectives are central. Durable provisioning and reconciliation are needed before safe concurrent control-plane scaling. Requirements should follow the intended workload and tenancy model.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C092 — SUPPORTED

```text
All live evidence comes from disposable kind labs on one host. Replication is asynchronous, local volumes are node-affine, MinIO shares the host and the API lacks durable operations. Off-site recovery, replication credential rotation and notification delivery remain NOT VALIDATED. Instrumentation is incomplete. The recorded working tree was dirty, so its Git hash alone is incomplete provenance. [Environment](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/environment.json).
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C093 — SUPPORTED

```text
**Planned:** independent storage and object-store recovery drills; resolution or bounded acceptance of the replica anomaly; replication credential rotation; complete metric and notification paths; durable API operations; supported release/upgrade procedures; representative repeated workload tests. **Experimental:** current restore and failure harnesses outside their recorded profile. No future item is counted as an implemented production capability.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C094 — SUPPORTED

```text
Treat backup success and recoverability as separate assertions. Observe recovery from clients as well as the database. Keep restore archive history separate after promotion. Diagnose host resource limits before changing credentials or disabling certificate checks. Preserve failed attempts, and distinguish an actual fix from a failure that did not recur. These lessons are supported by the [failure record](failure-engineering.md), not inferred from idealized diagrams.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C095 — SUPPORTED

```text
The project demonstrates an implemented PostgreSQL DBaaS provisioning path and measured behavior under controlled failures. Its strongest contribution is a traceable engineering loop: implement, validate, inject faults, retain contrary evidence and narrow claims to what the observations support. Production readiness remains a separate body of work. [Current status](../evidence/project-status.md).
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

## docs/portfolio/linkedin-project.md

### C096 — SUPPORTED

```text
- **GitHub:** Cloud-Native PostgreSQL Database-as-a-Service Platform. Keep “research prototype” in the opening paragraph: the implemented provisioning path justifies DBaaS, while the qualifier sets the right boundary.
- **LinkedIn:** Building and Testing a PostgreSQL DBaaS on Kubernetes. This puts implementation and experimentation at the center.
- **Resume:** Kubernetes-Native PostgreSQL DBaaS Prototype. Compact, technically specific and honest about production maturity.
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C097 — SUPPORTED

```text
“Highly Available PostgreSQL Platform on Kubernetes” puts too much weight on HA given the shared physical failure domain and unresolved historical replica anomaly. Prefer the implemented DBaaS workflow and measured failure engineering as the main story.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C098 — PARTIALLY SUPPORTED

```text
Built a PostgreSQL DBaaS prototype using FastAPI, Helm, Patroni, PgCat, WAL-G and MinIO. Validated provisioning, SQL routing, backup and target-time recovery in disposable Kubernetes labs, then tested node loss, client reconnects, clone durability and credential rotation. Published raw evidence, measured charts and unresolved failures alongside the implementation.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).
- **Recommended wording:** Limit retention claims to the observed acknowledgement set; async replication does not guarantee zero RPO.

### C099 — SUPPORTED

```text
I started with a PostgreSQL DBaaS on Kubernetes: a browser UI and FastAPI control plane deploying Helm releases, with Patroni for database leadership, PgCat for connections, and WAL-G plus MinIO for backup and WAL storage.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C100 — SUPPORTED

```text
In my disposable multi-node lab, I exercised voluntary drains, abrupt worker loss, persistent SQL clients, isolated target-time restores, clone restarts and application credential rotation. All nodes were containers on one host, so the results describe that lab rather than independent host or zone resilience.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C101 — SUPPORTED

```text
- Kubernetes API EOF errors traced to host inotify exhaustion and failed kube-proxy initialization.
- Backup error handling could report success without a valid primary target.
- A writable restore clone needed to stop following the source archive after bootstrap.
- A configuration watcher kept a proxy pod alive after PgCat had already exited.
- An alert based only on Patroni's primary role missed a stopped PostgreSQL process.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C102 — SUPPORTED

```text
I corrected those paths and retained regression and runtime evidence. I also kept the failure I cannot yet explain: one historical replica needed manual reinitialization after node loss. Three later clean runs recovered automatically, but that does not establish a root cause or a fix.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C103 — SUPPORTED

```text
Observed during controlled failure testing: four clients acknowledged 20,624 writes, with 34 failed transactions and 19 reconnects; none of the acknowledged IDs were missing afterward. This does not establish zero RPO. [Source](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json).
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C104 — SUPPORTED

```text
The paired backup sample measured about 1,232 TPS at baseline and 1,153 TPS during backup, a calculated 6.40% reduction. Those are short shared-host samples, not a capacity guarantee. [Source and methodology](../report/performance-results.md#backup-impact).
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C105 — SUPPORTED

```text
The repository includes Mermaid architecture sources, generated charts, raw results, a claims register and production gaps. Seven scrape targets remain broken; off-site recovery, replication credential rotation and notification delivery remain unvalidated.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C106 — SUPPORTED

```text
The main lesson: measure promotion, client recovery and full replica convergence separately—and preserve the evidence that does not fit the success story.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C107 — SUPPORTED

```text
Use the [ten-slide carousel](linkedin-carousel.md), with architecture and measured charts rather than fabricated dashboard screenshots. Link the repository's actual public URL when publishing; no URL or publication is assumed here. All numbers and claim boundaries are governed by the [claims register](../evidence/claims-register.md).
```

- **Expected evidence:** Clean installation/builds, committed file inventory and source/export correspondence.
- **Found:** Clean working candidate builds; current HEAD lacks most candidate files; cached builds are not bit-reproducible. [Artifact](../../results/validation/phase6-5/clean-builds.txt).

## docs/portfolio/resume-project.md

### C108 — SUPPORTED

```text
**One line:** Built and experimentally evaluated a PostgreSQL provisioning platform with FastAPI, Helm, Patroni, PgCat and WAL-G on Kubernetes.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C109 — PARTIALLY SUPPORTED

```text
- Built an authenticated FastAPI and browser provisioning path with namespace restrictions, Helm validation, Secret references and explicit partial-failure reporting.
- Designed and validated role-aware PostgreSQL connections, streaming replication and multi-proxy behavior in a disposable Kubernetes lab.
- Implemented and validated isolated target-time recovery with separate PVC identities, source preservation and restored-data checks across graceful and abrupt clone replacement.
- Built persistent-client failure tests that compare acknowledged transaction IDs after node loss; retained failed operations and recovery milestones as separate evidence.
- Corrected backup false-success risk, proxy-watcher termination behavior and stopped-primary alert logic, with regression checks and scoped runtime evidence.
- Measured backup impact at 1,232 → 1,153 TPS in a short paired lab sample; documented the calculated 6.40% reduction and measurement limits.
- Published reproducible architecture sources, measured charts and a failure register retaining an unresolved historical replica anomaly alongside three successful clean reruns.
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).
- **Recommended wording:** Describe a short single-host observation, not average overhead, capacity or causal proxy cost.

### C110 — SUPPORTED

```text
Use “prototype” and “disposable lab” when discussing scope. Do not convert observed acknowledgement retention into a zero-RPO claim or the measured recovery milestones into an SLA. This package describes repository outcomes; it does not imply a production employer deployment.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

## docs/portfolio/linkedin-carousel.md

### C111 — SUPPORTED

```text
Ten slides; use concise captions and the actual exported assets below. Images illustrate architecture or measured data, never a fabricated running dashboard. Source and evidence links belong in speaker notes or the accompanying post.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C112 — SUPPORTED

```text
A PostgreSQL DBaaS prototype: UI → FastAPI → Helm → database services. State “disposable lab validation” on the slide.
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C113 — SUPPORTED

```text
Separate provisioning responsibility from SQL, replication and recovery. All kind nodes share one host.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C114 — SUPPORTED

```text
Validate inputs, authenticate, lint charts, deploy in order, wait for readiness and report partial completion.
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C115 — SUPPORTED

```text
Leadership, SQL readiness and client recovery are different milestones. PDBs govern voluntary evictions.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C116 — SUPPORTED

```text
Base backup plus archived WAL; assert before/after-target data and a new write. Off-site recovery remains unvalidated.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C117 — SUPPORTED

```text
Show measured promotion and client milestones from the continuation run; include the single-host qualification.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C118 — SUPPORTED

```text
Explain watcher shutdown and archive separation corrections. Name the historical replica failure as unresolved despite three clean reruns.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C119 — SUPPORTED

```text
Use the backup comparison: 1,232 → 1,153 TPS, calculated 6.40% lower. One short paired observation.
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C120 — SUPPORTED

```text
A passing command is insufficient: combine SQL assertions, object evidence, acknowledgements and recovery state.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C121 — SUPPORTED

```text
Independent storage/failure domains, off-site restore, durable control plane, complete telemetry, tenant identity and defined recovery objectives.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C122 — SUPPORTED

```text
Slide 6 uses [failover windows](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json); slide 8 uses [backup measurements](../report/performance-results.md#backup-impact). Architectural sources are listed in the [diagram catalog](../architecture/README.md). Slide 7 is an explanatory diagram, not a trace of the unresolved replica failure. Use readable crops without removing axis units, measurement scope or limitation captions. See [production gaps](../report/production-gap-analysis.md) for slide 10.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

## docs/portfolio/interview-talking-points.md

### C123 — SUPPORTED

```text
Use these as technical explanations, with claim scope from the [evidence index](../evidence/README.md). Answers describe the current prototype; redesign ideas are explicitly Planned.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C124 — SUPPORTED

```text
A StatefulSet supplies stable identities and volume associations. It does not decide which PostgreSQL instance may be writable, configure replication or orchestrate promotion. Patroni adds database-aware role management through Kubernetes DCS state. Both layers matter: the drain experiments showed that correct leadership does not make a local PVC portable.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C125 — SUPPORTED

```text
Members coordinate through Kubernetes DCS state and leadership ownership. A member needs the appropriate leadership state and database eligibility before promotion; observed roles then drive Service routing. The harness polls leadership rather than instrumenting every internal election step, so reported promotion time includes observation delay.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C126 — SUPPORTED

```text
Leadership ownership, refresh/demotion behavior and replica eligibility are core mechanisms. Their safety still depends on DCS behavior and partition/fencing assumptions. This repository has not proven all network-partition, process-pause or storage-loss cases. I would review effective Patroni settings and test both sides of a partition before making a split-brain guarantee; a PDB or a Service label cannot supply that proof.
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C127 — SUPPORTED

```text
The remaining members can promote an eligible replica and routing follows the new role. Existing connections may fail until client timeouts and reconnects complete. The returned worker also has to converge onto the current history. One original run restored SQL but failed replica convergence; three clean later runs converged without reinitialization. These are different outcomes within the same broad fault category.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C128 — SUPPORTED

```text
The exact trigger is unknown. Diagnostics captured a request for WAL position 0/14000000 on timeline 4 while the primary flush position was 0/130799C8. That explains why the state deserved investigation, but does not establish how it arose. Manual reinitialization restored the member; it is remediation, not a root-cause fix.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C129 — SUPPORTED

```text
I know the initial automatic convergence failed, the diagnostic positions differed and reinitialization restored redundancy. I know three later clean runs converged automatically. I do not know the precise preceding transition or whether a particular timing, timeline or archive interaction was necessary. The honest classification is UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C130 — SUPPORTED

```text
It supplies a connection-pooling and role-routing layer while letting the control plane expose a consistent endpoint. The project measures its costs and failure behavior instead of assuming throughput improvement. An early mixed workload exposed session-pooling behavior when a read-first session later attempted a write; the final benchmark deliberately uses transaction pooling.
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C131 — SUPPORTED

```text
A Service with a healthy peer can send new connections to that peer. Existing TCP sessions on the lost pod do not move and may fail. The client must reconnect and decide what to do with uncertain transactions. Shutdown testing also found that the watcher could outlive PgCat; bounded signal handling fixed that container-lifecycle defect without shortening the database client drain grace.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C132 — SUPPORTED

```text
Each client writes a unique ID and records it only after commit acknowledgement. After recovery, the harness compares those IDs with database rows. This establishes retention of the observed acknowledgement set. It does not establish that every failed transaction rolled back; a connection can fail after commit but before the acknowledgement reaches the client, so uncertain transactions are not silently retried.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C133 — SUPPORTED

```text
Promotion is when a new primary is observed. SQL recovery is a separate probe becoming usable. A held client may recover later because it is waiting on a stale TCP connection, pool backend or timeout. Full member convergence is later still. The performance report labels these boundaries and notes that client errors can continue after the independent probe succeeds.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C134 — SUPPORTED

```text
PostgreSQL generates WAL and the configured archive path uses WAL-G to send completed segments to object storage. The test forces a segment switch and checks both archiver progression and the segment object. That verifies the tested path; completeness for a future restore target also depends on retention, continuity and available base backups.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C135 — SUPPORTED

```text
Choose a base backup completed before the requested UTC target, restore it and replay the necessary archived WAL until the target before promotion. The meaningful test is data semantics: a before-target marker exists, a later marker is absent and a new write succeeds. Backup-command exit status alone cannot demonstrate that.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C136 — SUPPORTED

```text
Bootstrap needed source WAL, but the earlier configuration continued exposing a source restore command during later recovery. A writable clone develops its own history, making later source reads unsafe. The original clone checkpoint failure motivated the correction; complete causality for that crash is not claimed.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C137 — SUPPORTED

```text
The clone reads source archives during bootstrap, then disables subsequent source recovery reads, archive writes and scheduled backups. The durability test checks recovered rows and clone writes after graceful and abrupt replacements while excluding later source-only data. Credentials are still mounted, so configuration separation is not equivalent to IAM revocation.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C138 — SUPPORTED

```text
A new release and new PVC identities preserve the source for comparison and rollback. Ownership checks reject an existing target, reducing accidental overwrite risk. It still consumes resources and needs a deliberate write boundary, endpoint cutover and rollback decision. In-place recovery remains a separate destructive workflow with explicit execution controls.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C139 — SUPPORTED

```text
The final paired sample recorded lower TPS and higher mean latency while the official backup Job ran. The reporting script calculates the relative TPS change from raw data. Shared CPU/storage, cache state and short sampling mean the result is an observed association, not a universal backup overhead estimate. See the performance report for values and retained resource counters.
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C140 — SUPPORTED

```text
It records completed transactions, TPS and mean latency for the exact direct/proxy routes, workload scripts, concurrency and configuration used in that lab. It also exposed a workload/pooling mismatch before the final run. The completed matrix supports transparent comparisons within the recorded environment.
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C141 — SUPPORTED

```text
It does not establish production capacity, percentile latency, statistical significance, cold-cache behavior, a general scaling curve or that PgCat is faster. Each point is a single short small-dataset sample. Missing percentile and reconnect measurements stay null rather than being inferred.
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C142 — SUPPORTED

```text
Diagnostics showed host inotify exhaustion, failing kube-proxy initialization and unhealthy DNS. Token and CA availability did not explain the failure. Temporarily increasing the host limit and restarting only owned components restored CA-verified Kubernetes access. The evidence supports this diagnosis for that environment; it is not a rule that every EOF has the same cause.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C143 — SUPPORTED

```text
The host limit constrained creation of inotify instances used by containerized processes. A fresh diagnostic process returned errno 24 even with few ordinary descriptors, and kube-proxy logs reported initialization failure. That disrupted Service networking and coincided with unhealthy DNS. Raising the relevant host limit, rather than merely changing a process file-descriptor setting, restored the tested path.
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C144 — SUPPORTED

```text
The physical lab host and local MinIO are shared failure domains. The API workflow has no durable operation service or proven multi-replica coordination. Default PgCat replica count is smaller than the HA test profile. Node-affine storage can leave a member unavailable until its worker returns. A production assessment must consider Kubernetes control-plane and storage topology beyond the kind diagram.
```

- **Expected evidence:** API code, rendered resources, concurrent requests and partial failure.
- **Found:** Different releases succeed; serial duplicates upgrade; same-name pair yields one error; partial PgCat failure preserves completed releases. [Artifact](../../results/validation/phase6-5/live/partial-failure.json).

### C145 — SUPPORTED

```text
Independent storage/failure domains, verified off-site restore, explicit TLS/identity boundaries, durable operations, a supported upgrade strategy, complete observability and alert delivery, and workload-specific objectives. The replica anomaly needs resolution or explicit residual-risk handling. Shared DBaaS additionally requires tenant authorization and quotas. The gap analysis ranks these gates.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C146 — SUPPORTED

```text
Planned: define a database CRD with topology, Secret references and storage policy, plus status conditions and observed generation. Reconcile idempotently with ownership checks and durable progress rather than depending on a request remaining alive. Separate destructive recovery into an explicit operation resource with immutable source/target identities. Introduce concurrency controls and upgrade state transitions before adding automation.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C147 — SUPPORTED

```text
Planned: authenticate individual tenant identities, authorize every operation against resource ownership, enforce quotas and constrain database roles, namespaces, network and storage access. Keep operator privilege separate from tenant requests and record an audit trail. Namespace allowlisting and a shared Bearer token are useful operator controls but insufficient tenant isolation.
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C148 — SUPPORTED

```text
Planned: write or replicate backups/WAL into an independently administered failure domain with explicit retention, encryption and least-privilege credentials. Restore into a fresh cluster that does not depend on source-local storage, assert target-time data and record all milestones. Test missing WAL, credential failure and retention errors too. The existing external helper is configuration capability; external recovery remains NOT VALIDATED.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C149 — SUPPORTED

```text
Start with the application durability and availability contract. Define which acknowledged writes may be lost, which failure domain is covered and which service milestone ends recovery. Measure replication/archive lag and restore completeness for RPO; measure detection, promotion or restore, routing and application recovery for RTO. Report distributions across realistic repeated drills rather than selecting a favorable lab point.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C150 — SUPPORTED

```text
No. They are observations in a disposable shared-host environment with explicit workloads and probe boundaries. An SLA needs an agreed service definition, measurement window and operational commitment. This project has no established numerical production availability, RPO or RTO promise.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C151 — SUPPORTED

```text
- Leadership, clients, replica anomaly and clone separation: [failure engineering](../report/failure-engineering.md), with linked raw experiments.
- Throughput, backup cost and timing semantics: [performance report](../report/performance-results.md).
- API EOF and host limits: [Phase 4 diagnosis](../audit/phase4-runtime-validation-report.md#kubernetes-api-eof-root-cause).
- Current identity/provisioning implementation: [application README](../../application/README.md).
- Operator, tenancy, off-site and objective design: [production gaps](../report/production-gap-analysis.md); these are future decisions.
```

- **Expected evidence:** Raw pgbench measurements and controlled comparison methodology.
- **Found:** All 24 raw TPS values match; backup pair recomputes to 6.395908%. No repeated samples, dedicated warm-up or equivalent-backend routing control. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

## docs/portfolio/interview-stories.md

### C152 — SUPPORTED

```text
These describe repository engineering events, not an employer production incident or independently verified business impact.
```

- **Expected evidence:** Clean installation/builds, committed file inventory and source/export correspondence.
- **Found:** Clean working candidate builds; current HEAD lacks most candidate files; cached builds are not bit-reproducible. [Artifact](../../results/validation/phase6-5/clean-builds.txt).

### C153 — SUPPORTED

```text
**Situation:** Provisioning could not reliably reach the Kubernetes API despite available credentials.
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C154 — SUPPORTED

```text
**Action:** Compared network, DNS, token/CA and host-resource evidence; found inotify creation failures and kube-proxy initialization errors. Temporarily adjusted the host limit and restarted only owned components.
```

- **Expected evidence:** Enforcing CNI denial and positive reachability checks.
- **Found:** Four paths timed out; normal SQL, DNS and API access succeeded with explicit review policies. [Artifact](../../results/validation/phase6-5/live/network.json).

### C155 — SUPPORTED

```text
**Result:** CA-verified Kubernetes access and provisioning passed. The host setting was restored during cleanup; the diagnosis became a documented lab prerequisite.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C156 — SUPPORTED

```text
**Situation:** Static review found backup target selection and error handling that could allow a misleading success.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C157 — SUPPORTED

```text
**Task:** Make completion mean that a valid primary command actually ran, then verify more than exit status.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C158 — SUPPORTED

```text
**Action:** Added strict selection of a unique primary, authenticated role checking and propagated failures; retained regression coverage and tested official backup Jobs, catalog metadata and restored data.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C159 — SUPPORTED

```text
**Result:** The path now fails on invalid selection and has scoped backup/restore evidence. No historical data loss or production incident is claimed.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C160 — SUPPORTED

```text
**Situation:** An isolated clone later failed checkpoint recovery after worker loss; source archive coupling was unsafe after promotion.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C161 — SUPPORTED

```text
**Task:** Separate bootstrap recovery from subsequent clone history and prove data survives replacement.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C162 — SUPPORTED

```text
**Action:** Disabled later source-WAL reads, clone archive writes and scheduled backups; checked source identities and target-time markers across graceful and abrupt clone replacement.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C163 — SUPPORTED

```text
**Result:** The later clone retained recovered and new rows while excluding later source data. The full original crash cause remains uncertain, and mounted storage credentials remain a separate limitation.
```

- **Expected evidence:** Authentication/input tests, Secret handling, RBAC and credential lifecycle checks.
- **Found:** Tests and code support operator authentication and private files, not tenant authorization or full TLS; historical credentials need review. [Artifact](../../results/validation/phase6-5/history-credential-locations.json).

### C164 — SUPPORTED

```text
**Situation:** A successful new SQL probe could obscure the experience of existing client connections.
```

- **Expected evidence:** Implementation and scoped runtime evidence consistent with stated limitations.
- **Found:** Source/chart inspection and historical evidence support the prototype design; fresh same-namespace markers verify separate routes, not production availability. [Artifact](../../results/validation/phase6-5/live/isolation.json).

### C165 — SUPPORTED

```text
**Action:** Ran clients outside the failed worker, recorded unique IDs after commit acknowledgement, bounded connection behavior and compared acknowledged IDs after recovery without replaying uncertain operations.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C166 — SUPPORTED

```text
**Result:** The continuation run retained its acknowledged set while recording failed transactions and reconnects. The report distinguishes promotion, probe recovery and client recovery rather than claiming uninterrupted service.
```

- **Expected evidence:** Client commit ordering, unique IDs and post-recovery database comparison.
- **Found:** Inspected client records success after commit; 20,624 unique per-client successes, 34 failures and no missing acknowledged IDs in that historical run. [Artifact](../../results/validation/phase6-5/measurement-audit.json).

### C167 — SUPPORTED

```text
**Situation:** The original abrupt-loss test restored a primary but left a replica stuck until manual reinitialization.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C168 — SUPPORTED

```text
**Task:** Investigate and retain evidence while testing whether clean runs reproduce the failure.
```

- **Expected evidence:** Clean installation/builds, committed file inventory and source/export correspondence.
- **Found:** Clean working candidate builds; current HEAD lacks most candidate files; cached builds are not bit-reproducible. [Artifact](../../results/validation/phase6-5/clean-builds.txt).

### C169 — SUPPORTED

```text
**Action:** Captured timeline/WAL diagnostics, restored redundancy explicitly and ran clean automatic-recovery trials with separate artifacts. Avoided rewriting the earlier result after later success.
```

- **Expected evidence:** Backup objects/catalog, restored row state, source ownership and failure-path guards.
- **Found:** Historical row/restart evidence plus fresh isolated clone and six backup scenarios; metadata does not prove full WAL coverage for destructive recovery. [Artifact](../../results/validation/phase6-5/live/clone.json).

### C170 — SUPPORTED

```text
**Result:** Three later clean runs recovered without reinitialization. The original cause remains unknown: UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS.
```

- **Expected evidence:** Clean installation/builds, committed file inventory and source/export correspondence.
- **Found:** Clean working candidate builds; current HEAD lacks most candidate files; cached builds are not bit-reproducible. [Artifact](../../results/validation/phase6-5/clean-builds.txt).

## README capability table

| Exact claim | Classification | Expected and found evidence | Recommended boundary |
|---|---|---|---|
| “Authenticated provisioning; streaming replication; SQL through PgCat; backups and WAL; isolated PITR; restart durability; enforced network policies; application credential reload” | SUPPORTED | Code and historical per-capability runtime artifacts; fresh provisioning, backup, clone and policy probes corroborate a subset | LIVE VALIDATED applies to named experiments, not every configuration |
| “Multi-node failure behavior, local monitoring, benchmark and recovery measurements; bounded operator scripts rather than a complete managed lifecycle” | SUPPORTED | Historical failure/monitoring artifacts and raw benchmarks; explicit limitations match implementation | Keep EXPERIMENTAL / PARTIAL |
| “Independent off-site recovery, replication credential rotation, notification delivery, production failure domains and end-to-end TLS” under NOT VALIDATED | SUPPORTED | No complete evidence was found for those capabilities | Keep NOT VALIDATED |

## Confirmed inconsistencies corrected in this phase

| Document | Finding/classification before correction | Evidence found | Correction |
|---|---|---|---|
| README PITR | MISLEADING if read as complete recoverability preflight | Simulated past target reaches destructive boundary without WAL proof | Explicit incomplete WAL coverage warning; future targets now rejected |
| docs/security/api-security.md | MISLEADING universal response-header description | Auth failures return before downstream headers | Exclude early 401/503 responses from no-store/nosniff assertion |
| docs/security/security-model.md | OUTDATED absence of policies/drills/build proof | Later lab artifacts and fresh builds | Distinguish historical Phase 2 scope from later evidence |
| monitoring/README.md | OUTDATED alert-validation scope | Later transition results plus failed scrape-fault experiment | Retain both successful scope and later failed attempt |
| docs/operations/version-matrix.md | OUTDATED monitoring installation/pinning statement | dependency checksum and prior deployed monitoring evidence | Describe actual pinned package and remaining uninstalled components |
| docs/testing/resilience-validation.md | OUTDATED single small restore relation | 100k/440k rows, 113.8/500.7 MiB raw results | Document both points, not a scaling curve |
| docs/operations/restore-cutover.md | OUTDATED clone restart status | Graceful and abrupt replacement data assertions | Record bounded durability proof; exclude disk loss |
| docs/diagrams/multinode-topology.mmd | MISLEADING fixed proxy/member arrows | PgCat uses shared primary/replica Services | Correct source and SVG/PNG traffic paths |
| docs/report/performance-results.md | PARTIALLY SUPPORTED comparison interpretation | No warm-up, randomization or catch-up barrier; unequal backend routing | Add limits; synchronize generator text |

The exact current wording appears in those files. Earlier historical result artifacts were retained, not rewritten to agree with the corrections.

## Interpretations that remain unsupported

Production readiness, zero RPO, a guaranteed recovery time, split-brain impossibility, average 6.40% backup overhead, strong tenant isolation, complete secret-history clearance, complete WAL preflight and bit-reproducible builds are **UNSUPPORTED**. The public documents generally already disclaim these interpretations. [Publication conditions](publication-readiness.md) prevent the project title or polished assets from implying them.
