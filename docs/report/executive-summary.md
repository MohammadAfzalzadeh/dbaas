# Executive summary

## A database service, tested beyond deployment

This project implements a PostgreSQL Database-as-a-Service prototype on Kubernetes. A browser interface calls an authenticated FastAPI control plane, which validates operator inputs and deploys Helm releases. Patroni manages PostgreSQL replication and leadership. PgCat supplies connection pooling and routing. WAL-G writes base backups and archived WAL to an S3-compatible destination; the validated lab uses MinIO.

The engineering objective was to make an existing research repository understandable, repeatable and testable under failure. A successful deployment is only the starting point. The project asks whether clients can use the service, whether backups restore the intended data, what happens during maintenance and abrupt loss, and which observations justify a public claim. The resulting package includes implementation, regression checks, raw runtime artifacts, measured charts and an explicit record of unresolved failures.

The [evidence index](../evidence/README.md) is the authority for validation scope. The [engineering report](engineering-report.md) explains the implementation, and the [failure report](failure-engineering.md) records successful and unsuccessful experiments together. This is a technically evaluated prototype; it carries no availability, capacity or recovery guarantee.

## Architecture and its limits

The control plane authenticates an operator token, restricts namespaces, validates requested configuration and invokes Helm. It checks charts before mutation and waits for resource readiness. Credentials normally arrive through existing Kubernetes Secrets. Temporary Helm values are held in private files, previews are redacted and partial completion is reported. This makes the workflow usable and inspectable, but it remains synchronous orchestration. Durable jobs, provisioning locks and continuous reconciliation are future work.

The measured multi-node profile used three PostgreSQL members and two PgCat replicas across three workers. Every kind node was a container on the same Docker host. Database volumes used local-path storage and remained attached to their original worker. These choices allowed controlled node-container failures and placement tests while imposing an important boundary: the experiment does not demonstrate independent host, disk or availability-zone resilience. [Environment](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/environment.json).

Patroni coordinates database roles through Kubernetes. StatefulSets preserve pod identity and storage relationships; they do not elect a PostgreSQL leader. PgCat gives clients a stable connection layer, but an existing TCP session can still fail when its proxy or backend disappears. Asynchronous replication means successful acknowledgement retention in an experiment cannot establish zero RPO.

## What the evidence establishes

Authenticated provisioning produced a usable database service. SQL checks observed replication and role-aware routing. Calico allowed required traffic and denied unrelated and cross-release probes in the tested policy profile. Official backup Jobs produced WAL-G metadata and objects, and switched WAL segments appeared in object storage. Recovery checks asserted actual row state rather than relying on a successful command exit. [Capability register](../evidence/README.md#capability-register).

Target-time recovery retained a before-target row, excluded a later row and accepted a new write. Isolated restore used a separate release and PVC identities while preserving source identities. After correcting archive separation, the clone retained recovered and newly written data across both graceful and abrupt replacement. The clone was a single-member recovery target; this was not an off-site disaster-recovery drill. [Durability evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json).

Application credential rotation was tested through database and proxy reload behavior: new credentials worked, old credentials failed on new connections and held sessions continued. This distinguishes login rotation from revocation of established sessions. Replication, administrative and object-store credential rotation are outside that result. [Rotation evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/rotation-reload/attempt-1/result.json).

## Selected disposable-lab measurements

Provisioning completed in **171.647 seconds** in the continuation lab. The duration includes this environment's deployment path and is not a provisioning SLA. [Provisioning result](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/provisioning.json).

During the four-client abrupt-loss experiment, promotion was observed at **24.378 seconds** and an independent SQL probe succeeded at **24.554 seconds**. The clients acknowledged **20,624 writes**, recorded **34 failed transactions** and **19 reconnects**, and had no acknowledged IDs missing afterward. Failed operations were not blindly replayed. Client recovery and full member convergence remained separate milestones. [Failover windows](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json).

The final benchmark contains **24 completed samples** across direct/PgCat routes, read-heavy/write-heavy/mixed profiles and several concurrency settings. Each point is one short sample on a small dataset. For mixed traffic at ten clients, direct PostgreSQL observed **1401.014 TPS**, compared with **1158.075 TPS** through PgCat. The result does not support a claim that adding a proxy makes this workload faster. [Performance report and raw-source links](performance-results.md).

A paired workload measured **1231.640 TPS** without backup and **1152.865 TPS** during backup: a reporting-script calculation gives **6.40% lower TPS**. Shared resources and short sampling prevent treating that difference as an isolated causal cost. Two compressible payload relations, **113.8 MiB** and **500.7 MiB**, restored and passed writable/data checks in **15.181** and **16.499 seconds**. The durations include bootstrap and assertions, not replay alone. [Backup and recovery measurements](performance-results.md#backup-impact).

## What broke, and why it matters

A Kubernetes API EOF problem initially resembled an access or certificate issue. Diagnostics instead found host inotify exhaustion, failed kube-proxy initialization and unhealthy DNS. A temporary host-limit adjustment and restart of owned components restored CA-verified access. The solution did not require disabling TLS verification or broadening the application to cluster administrator. [Runtime diagnosis](../audit/phase4-runtime-validation-report.md#kubernetes-api-eof-root-cause).

Static review found a backup false-success risk: selector and command-error handling could allow an invalid operation to appear successful. Strict selection, authenticated role checks and propagated failures corrected that path. Restore experiments exposed a separate archive-isolation risk: a writable clone must not continue following divergent source WAL after bootstrap. Proxy termination tests showed that the watcher could keep a pod alive after PgCat exited; bounded signal handling corrected the watcher behavior while preserving proxy drain time. An alert expression also required correction because Patroni's primary-role metric stayed true when PostgreSQL was stopped. [Defects and regression evidence](failure-engineering.md#development-defects-and-regression-evidence).

One historical replica recovery failure remains open. The initial abrupt-loss run restored a writable primary but left a replica stuck in archive recovery until manual reinitialization. Three later clean runs recovered automatically, yet the exact earlier trigger remains unknown. Its classification is **UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS**. Successful reruns do not justify calling it fixed. [Anomaly record](failure-engineering.md#the-unresolved-replica-recovery-anomaly).

## Remaining work and portfolio value

Seven scrape targets refused connections in the final inventory. Actual dashboards cover available component metrics, but SQL/API instrumentation and recovery-chain visibility remain incomplete. Availability and backup alert transitions have live evidence; notification delivery does not. A later scrape-fault alert attempt failed, and subsequent harness hardening has static tests only. [Exact monitoring gaps](observability-gaps.md).

Production deployment would require independent storage/failure domains, verified off-site restore, defined recovery objectives, trusted transport and identity boundaries, durable control-plane operations, supported upgrade procedures and representative repeated testing. Multi-tenancy would add authorization, quotas and ownership controls beyond a namespace allowlist. These are explicit deployment gates, not capabilities inferred from the project title. [Production gap analysis](production-gap-analysis.md).

The strongest portfolio story is the engineering process: build a usable service, test its failure boundaries, identify defects with concrete observations, retain contradictory evidence and communicate what remains unknown. The repository supports that story without turning limited lab observations into production promises.
