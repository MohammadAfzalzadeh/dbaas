# Executive Summary

This repository implements a Cloud-Native PostgreSQL DBaaS prototype: FastAPI and Helm provision a Patroni/PostgreSQL data plane with PgCat, WAL-G and MinIO. Controlled lab experiments validate provisioning, SQL, backup, target-time recovery and selected failure behavior. The package preserves failures and distinguishes lab measurements from production guarantees.

[Executive briefing](executive-summary.md) · [Evidence authority](../evidence/README.md) · [Failure register](failure-engineering.md)

# 1. Problem Statement

Deploying a PostgreSQL pod does not establish a database service. Operators need repeatable provisioning, usable connection endpoints, role-aware recovery, recoverable backups and evidence of what clients experience during faults. This project turns an existing Kubernetes/PostgreSQL research repository into an inspectable DBaaS prototype without replacing its working chart interfaces.

# 2. Project Goals

Preserve existing deployments, correct configuration and backup failure paths, constrain privileged operations, test recovery against deterministic data, and retain unsuccessful experiments. The final package prioritizes traceable claims over impressive but unsupported availability language. [Claims register](../evidence/claims-register.md).

# 3. System Requirements

The lab requires Kubernetes, a working container runtime, persistent volumes, reachable image sources and a CNI that enforces NetworkPolicy for policy experiments. Local validation requires Helm, Python with the pinned application/script dependencies, and Node/npm. Image builds require Docker. Browser rendering is separate from runtime deployment. [Quick start](../../README.md#quick-start), [application configuration](../../application/README.md), [reporting tools](../../tools/reporting/README.md).

A healthy API process must not be confused with authenticated Kubernetes access. The application readiness endpoint checks local prerequisites; cluster reachability has a separate diagnostic path.

# 4. Architecture

![Architecture](../images/architecture/architecture.svg)

[Mermaid source](../diagrams/architecture.mmd). The browser calls FastAPI, which validates and deploys Helm resources. Patroni manages PostgreSQL roles; PgCat provides client pooling/routing; WAL-G sends base backups and WAL to MinIO in the tested lab. Monitoring observes supported component metrics. [Diagram catalog and decisions](../architecture/README.md).

The control plane is an operator-facing provisioning service. It is not a continuously reconciling Operator. The data plane can continue serving when the API is unavailable, but new provisioning depends on the API and Kubernetes control plane.

# 5. Control Plane

The API checks a shared Bearer token, namespace allowlist and request schema before creating releases. It lints selected charts first, then deploys dependencies in order and waits for StatefulSet readiness. Failure responses identify completed releases without claiming rollback. Private temporary directories and restrictive value-file permissions limit credential exposure during Helm execution.

Concurrent requests, API restarts and partially completed operations still need durable coordination. There is no tenant authorization or durable operation store. [API lifecycle and routes](../../application/README.md), [implementation](../../application/app/main.py), [provisioning observation](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/provisioning.json).

# 6. Kubernetes Resource Model

Helm renders StatefulSets, Services, Secrets references, ConfigMaps, backup CronJobs, RBAC, optional NetworkPolicies and disruption controls. Role Services select Patroni-managed database roles. PgCat has per-pod generated configuration state. The standalone and API chart families stay in their established paths for compatibility; both are checked during validation. [Repository map](../audit/repository-map.md).

Persistent volume identity is a recovery boundary. Helpers check release/namespace/resource ownership before destructive actions; replacing a pod is different from deleting its PVC. [Storage lifecycle source](../diagrams/storage-lifecycle.mmd).

# 7. PostgreSQL and Patroni

Patroni starts and manages PostgreSQL, replication and role state using Kubernetes as its DCS. The continuation baseline observed one primary and two streaming replicas. Replication is asynchronous, so a promoted replica may lack recent primary commits under other fault timings. [Baseline](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/baseline.json).

Database role, process health, streaming state and SQL assertions are separate signals. A primary-role metric can remain true when PostgreSQL is stopped; monitoring now checks process-running state too.

# 8. Leader Election and Failure Recovery

Patroni coordinates leadership through Kubernetes DCS state. Eligibility, leadership timing and database state affect promotion. Services follow role labels; clients and pools then need usable connections to the promoted backend. A StatefulSet supplies identity and placement, not PostgreSQL leader election.

Promotion, first successful independent SQL probe, persistent-client acknowledgement and complete member convergence are reported separately. The lab does not prove every network partition or fencing scenario. The initial stuck replica remains **UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS**, despite three later automatic recoveries. [Failure register](failure-engineering.md#the-unresolved-replica-recovery-anomaly).

# 9. PgCat

PgCat pools connections and routes to role-aware database Services. Each pod has an independent watcher that validates and atomically replaces generated configuration. Multiple proxy endpoints help new connections survive a proxy replacement; they do not migrate an existing TCP session.

An early session-pooling benchmark began on a replica and later attempted an update. The final mixed-workload profile uses transaction pooling; historical defaults remain compatible. That choice needs application compatibility testing for session state. The measured direct path was faster in the final matrix; pooling is not presented as a throughput improvement. [Performance results](performance-results.md).

# 10. Backup and WAL Archiving

The official backup CronJob selects exactly one primary, authenticates the role check and propagates failures. WAL-G writes a base backup and catalog metadata to the configured object store. PostgreSQL archival supplies the WAL needed between base backup and recovery target.

The harness checks Job completion, backup metadata, object keys and a switched WAL segment alongside archiver state. These observations verify the tested archive path; they do not prove every possible recovery target has a complete chain. MinIO shares the lab host failure domain. [Backup evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/backup/baseline.json), [WAL evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/backup/wal.json).

# 11. Point-in-Time Recovery

Recovery selects a base backup completed before an explicit UTC target, restores files and replays archived WAL to that boundary before promotion. Deterministic markers establish a meaningful assertion: before-target data must exist, later data must be absent and a new write must succeed.

The in-place workflow changes the source and requires explicit execution after plan review. The earlier single-node test is separate from later isolated restores. [In-place PITR evidence](../../results/runtime/pitr/result.json), [PITR source](../diagrams/pitr.mmd).

# 12. Isolated Restore

The isolated helper creates a new release with separate PVC identities, rejects an existing target and preserves source identities. Bootstrap reads the source backup/WAL; after promotion the clone disables later source archive reads, archive writes and scheduled backups. Mounted credentials remain an access risk until separately revoked or narrowed.

The corrected clone retained recovered and newly written rows across graceful and abrupt replacement while excluding source-only later data. This establishes the tested single-member clone behavior, not independent off-site recovery. Cutover remains an explicit operator decision with a write boundary and rollback plan. [Durability evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json), [cutover diagram](../diagrams/restore-cutover.mmd).

# 13. Security Architecture

The implemented boundary uses operator-token authentication, namespace allowlisting, namespaced RBAC, existing Secret references by default, private temporary values and redacted previews. Inline secrets require an explicit opt-in. NetworkPolicy limits selected traffic in the enforcing lab profile.

A shared operator token is not per-tenant identity. Kubernetes Secrets alone do not prove encryption at rest, and admission webhook TLS does not establish end-to-end SQL/API transport protection. [Security documentation](../security/), [final scan scope](../evidence/final-validation-summary.md), [production gates](production-gap-analysis.md).

# 14. Kubernetes Reliability

Readiness/startup probes, resource configuration, graceful termination, PDBs and scheduling controls are implemented and tested at different levels. A PDB constrains voluntary eviction; it cannot stop an abrupt node loss. The watcher fix bounds its own shutdown while retaining time for PgCat to drain clients. [Reliability audit](../audit/phase3-reliability-report.md), [shutdown evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/proxy-shutdown/attempt-2/result.json).

# 15. Scheduling and Failure Domains

The measured HA profile spreads three database members and two proxies over three workers. All workers and the control plane are containers on one physical host. Local-path PVCs remain tied to their worker, so a drained member cannot transparently move its data to another worker. [Topology](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/initial-topology.json), [drain observation](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/drain-replica.json).

This tests scheduling and node-container disruption, not independent rack, host, zone or storage failure. Chart defaults are smaller than the measured HA profile.

# 16. Network Isolation

Calico enforced the tested NetworkPolicies. Required SQL, replication, backup and API paths were allowed, while unrelated and cross-release database probes were denied. The default single-node CNI did not establish this boundary; enforcement evidence belongs to the multi-node profile. [Policy tests](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/network-policy.json).

Policy depends on namespaces, labels and CNI behavior. It is not sufficient proof of tenant authorization or complete egress isolation. [Trust-boundary diagram](../diagrams/network-boundaries.mmd).

# 17. Observability

The final inventory supports five dashboards and thirteen query expressions using actual component metrics. Seven scrape targets refused connections; exact endpoints and missing instrumentation are in [observability gaps](observability-gaps.md). [Inventory](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/observability-inventory.json).

Availability and backup conditions completed live transitions across distinct attempts. Initial alert logic missed a stopped database because a role metric remained true; the expression now combines role and running state. Notification delivery remains NOT VALIDATED. A later scrape-fault alert attempt failed; harness hardening afterward has static regression coverage only. [Failure report](failure-engineering.md).

# 18. Testing Methodology

Validation separates static, build, smoke, live and measured evidence. Unit tests exercise input boundaries and failure handling; chart lint/render checks examine manifests; image builds check recipes; live harnesses observe owned clusters. Failure attempts are append-only and retained separately from successful reruns.

Client acknowledgement sets, role checks, object metadata and restored rows provide complementary observations. Current Phase 6 checks do not refresh the historical live classification. [Final validation summary](../evidence/final-validation-summary.md), [test architecture](../diagrams/validation-architecture.mmd).

# 19. Failure Experiments

Experiments include database/proxy deletion, voluntary node drains, abrupt worker loss, target-time restore, clone restarts, credential rotation, backup under writes, policy probes and alert fault injection. Expected behavior, observed impact, known cause and final classification appear together in the [failure engineering report](failure-engineering.md).

The original abrupt-loss run restored a writable primary but failed full automatic member convergence. Later successful reruns are independent observations, not a replacement for that failure.

# 20. Persistent Client Testing

Clients record unique IDs after commit acknowledgement and verify those IDs after recovery. Failed operations remain uncertain and are not automatically replayed. In the continuation load run, four clients acknowledged 20,624 writes, with 34 failed transactions, 19 reconnects and no acknowledged IDs missing. [Raw windows](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json).

The test's timeout/reconnect behavior is part of the experiment. A new SQL probe can succeed before held clients recover; the after-probe window still included errors. This prevents confusing database promotion with complete application recovery.

# 21. Credential Rotation

The continuation changed an application role password and PgCat Secret, waited for projection/reload, and checked new and old credentials against the primary and each proxy. Held direct and proxy sessions continued; no database restart was requested and proxy pod identities stayed unchanged. [Rotation evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/rotation-reload/attempt-1/result.json).

Changing login credentials does not revoke established sessions. Replication, superuser and object-store credential rotation remain NOT VALIDATED. [Rotation diagram](../diagrams/credential-rotation.mmd).

# 22. Benchmark Methodology

The final matrix has 24 samples: direct and PgCat routes, three workload profiles, and concurrency 1/10/25/50. Each point is one ten-second scale-1 pgbench sample. Logical balances are reset, caches are not. The final mixed profile uses transaction pooling. [Raw matrix](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/pgbench.json).

Shared CPU/storage, run order, small dataset and lack of repeated samples limit inference. Mean latency is measured; percentiles and reconnect counts not emitted by this matrix remain null. Aborted session-pooling samples are preserved but excluded from completed-sample charts.

# 23. Performance Results

The [canonical performance report](performance-results.md) contains the full matrix and generated charts. For mixed traffic at ten clients, direct PostgreSQL observed 1401.014 TPS and PgCat 1158.075 TPS. Those observations support a comparison in this lab, not a universal ranking or production capacity claim. [Raw matrix](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/pgbench.json).

![Direct and proxy comparison](../images/results/final/direct-vs-pgcat.svg)

# 24. Backup Impact

The paired workload observed 1231.640 TPS at baseline and 1152.865 TPS during backup, a script-calculated relative change of −6.40%. Mean latency rose from 8.119 to 8.674 ms. [Raw backup sample](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/backup-impact.json), [calculated summary](../../results/validation/phase6/measured-summary.json).

Recorded resource counters provide context; the short shared-host pair does not isolate a causal backup tax or confidence interval. [Chart and methodology](performance-results.md#backup-impact).

# 25. Recovery Measurements

Payload relations of 113.8 and 500.7 MiB restored and passed writable/data checks in 15.181 and 16.499 seconds respectively. The payload compresses well; timings include scheduling, bootstrap and assertions, and do not isolate replay. [Smaller sample](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/restore-size/attempt-1/result.json), [larger sample](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/restore-size/attempt-2/result.json).

These points do not establish a scaling curve or external recovery time. WAL intervals include forced switches and exclude payload-generation WAL. [Complete measurement semantics](performance-results.md#restore-and-pitr-measurements).

# 26. Failures Found During Development

The [development defect register](failure-engineering.md#development-defects-and-regression-evidence) records **Symptom, Root cause, Fix, Regression test and Final status** for Kubernetes API EOF/inotify exhaustion, backup false-success risk, namespace/RBAC errors, PgCat naming/configuration, clone archive coupling, watcher shutdown and alert logic.

The replica recovery anomaly has an explicitly unknown root cause. Three later successful clean runs did not establish a fix. The scrape-fault attempt remains FAILED after static harness improvements. These are retained as first-class engineering outcomes rather than hidden in a successful aggregate.

# 27. Production Readiness Gap Analysis

[Production gaps](production-gap-analysis.md) separates critical gates, high-priority engineering, medium-priority operational work and optional product features. Independent storage failure domains, off-site restore, trustworthy transport/identity and agreed recovery objectives are central. Durable provisioning and reconciliation are needed before safe concurrent control-plane scaling. Requirements should follow the intended workload and tenancy model.

# 28. Limitations

All live evidence comes from disposable kind labs on one host. Replication is asynchronous, local volumes are node-affine, MinIO shares the host and the API lacks durable operations. Off-site recovery, replication credential rotation and notification delivery remain NOT VALIDATED. Instrumentation is incomplete. The recorded working tree was dirty, so its Git hash alone is incomplete provenance. [Environment](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/environment.json).

# 29. Future Work

**Planned:** independent storage and object-store recovery drills; resolution or bounded acceptance of the replica anomaly; replication credential rotation; complete metric and notification paths; durable API operations; supported release/upgrade procedures; representative repeated workload tests. **Experimental:** current restore and failure harnesses outside their recorded profile. No future item is counted as an implemented production capability.

# 30. Lessons Learned

Treat backup success and recoverability as separate assertions. Observe recovery from clients as well as the database. Keep restore archive history separate after promotion. Diagnose host resource limits before changing credentials or disabling certificate checks. Preserve failed attempts, and distinguish an actual fix from a failure that did not recur. These lessons are supported by the [failure record](failure-engineering.md), not inferred from idealized diagrams.

# 31. Conclusion

The project demonstrates an implemented PostgreSQL DBaaS provisioning path and measured behavior under controlled failures. Its strongest contribution is a traceable engineering loop: implement, validate, inject faults, retain contrary evidence and narrow claims to what the observations support. Production readiness remains a separate body of work. [Current status](../evidence/project-status.md).
