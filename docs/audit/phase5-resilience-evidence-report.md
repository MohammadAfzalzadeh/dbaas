# Phase 5 — Resilience and Evidence Report

Continuation results: [Phase 5 follow-up](phase5-continuation-report.md). Historical failed outcomes below remain preserved; see the follow-up for current validation scope.

Execution date: 2026-10-03. Existing uncommitted work preserved. No commit or push. Capability labels describe the specified scope only. PASS/FAIL in machine artifacts describes individual test outcomes; the initial setup and full abrupt-recovery sequence retain FAIL outcomes.

# Multi-Node Validation

**LIVE VALIDATED:** one control plane and three workers; three database members on distinct workers; two spread proxies; local-path RWO PVCs. Authenticated provisioning completed in 166.229 seconds. All nodes share one Docker host. Initial setup required an explicit inotify adjustment from 128 to 1024; this is not a clean unattended setup result. [initial-topology.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/initial-topology.json) [bootstrap-notes.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/bootstrap-notes.json)

# PostgreSQL HA

**LIVE VALIDATED:** baseline and final membership show one primary/two streaming replicas. **NOT VALIDATED:** complete automatic recovery after abrupt worker loss; one member required reinitialization. Replication is asynchronous. [baseline.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/baseline.json) [final-topology.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/final-topology.json)

# PgCat HA

**LIVE VALIDATED:** both proxies ready, independent configuration volumes, and 20 real Service connections distributed 4/16. **EXPERIMENTALLY MEASURED:** final abrupt deletion selected the proxy holding the persistent client session: 1 failed transaction, 1 reconnect, 0.203-second longest success gap, 95 acknowledged transactions and no missing IDs. The independent SQL probe succeeded after 0.223 seconds. Phase 4's one-proxy probe measured 3.942 seconds to its full post-failure checks; observers/topology/client settings differ, so this is not a controlled performance improvement ratio. [service-distribution.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/service-distribution.json) [pgcat-abrupt.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/pgcat-abrupt.json) [persistent-pgcat-abrupt.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/persistent-pgcat-abrupt.json)

# Node Drain

**LIVE VALIDATED:** replica and primary worker drains completed using eviction, without force or disable-eviction. PDB currentHealthy/desiredHealthy/disruptionsAllowed and Pending scheduling events are retained. Source local PVCs could not move; uncordoning allowed recovery. Replica drain completed in 93.731 seconds and membership stabilized at 105.425 seconds; primary drain completed in 93.702 seconds and stabilized at 106.503 seconds. These command observations include PgCat graceful shutdown. The promotion/SQL polls run after blocking drain and are upper bounds, not exact outage durations. [drain-replica.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/drain-replica.json) [drain-primary.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/drain-primary.json)

# Node Failure

**EXPERIMENTALLY MEASURED:** an owned primary worker was stopped abruptly and returned. New primary observed at 28.500 seconds; separate SQL probe at 28.660 seconds. The client had a 60.757-second longest success gap. One surviving replica stayed in archive recovery beyond 240 seconds; manual Patroni reinitialization restored streaming. Automatic complete recovery is **NOT VALIDATED**. Internal failure-detection time was not separately observed. [node-loss.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/node-loss.json) [recovery-followup.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/recovery-followup.json) [after-manual-reinitialization.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/after-manual-reinitialization.json)

# Network Policies

**LIVE VALIDATED:** Calico 3.28.2 enforced source SQL, replication, Kubernetes API, WAL-G/MinIO and monitoring flows; unrelated clients could not connect to PostgreSQL/MinIO, and the restore target could not access source SQL. MinIO remains a shared trusted namespace backup store, not tenant-isolated storage. Logging flow is **NOT VALIDATED** because it was not deployed. [network-policy.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/network-policy.json)

# Isolated Restore

**LIVE VALIDATED:** new release/PVCs, no source StatefulSet mutation, before-target row retained, later row absent and new write accepted. Fresh baseline restore measured 20.631 seconds. The first clone failed to restart after worker loss with checkpoint errors; source archive timeline collision is suspected, not conclusively proven. Ongoing clone archive reads and writes are now disabled after bootstrap; the helper checks live settings and can restart only the new clone to clear bootstrap settings. A fresh clone passed a pod restart in 13.868 seconds. Full abrupt-worker recovery of the corrected clone remains **NOT VALIDATED**. [isolated-restore.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/isolated-restore.json) [isolated-restart.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/isolated-restart.json)

# Off-Site Recovery

**STATICALLY VALIDATED:** provider-neutral `scripts/object-storage.py` generates a WAL-G Secret from existing credentials and endpoint/bucket/region/path-style/TLS options. `scripts/offsite-restore.py` renders/installs a fresh target with an explicit kubeconfig and existing Secrets. **NOT VALIDATED:** actual independent off-site backup and restoration; no external target was supplied. Local MinIO is not renamed or counted as off-site storage. [Guide](../operations/external-object-storage.md).

# Credential Rotation

**LIVE VALIDATED:** disposable PostgreSQL application role, Secret update, PgCat configuration update and coordinated rolling restart. New logins passed; old logins were rejected directly and through PgCat. Existing sessions are not implicitly revoked. Replication, superuser and object-store credential rotation are **NOT VALIDATED**. [Runbook](../operations/credential-rotation.md). [rotation.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/rotation.json)

# Upgrade Validation

**LIVE VALIDATED:** an OnDelete template revision left existing UIDs intact until explicit replacement. Replicas were replaced before the primary; max_connections became 200. PgCat and the single-replica API completed rolling replacements. The persistent client recorded 3 failures, 3 reconnects, 1,837 acknowledgements and a 2.649-second longest success gap, with none missing. Major PostgreSQL upgrade and multi-replica API concurrency are **NOT VALIDATED**. [upgrades.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/upgrades.json) [persistent-revision-rollout.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/persistent-revision-rollout.json)

# Persistent Client Results

**EXPERIMENTALLY MEASURED:** unique-ID INSERT/commit loop at a configured 0.1-second interval. Primary drain: 1,053 acknowledgements, 2 failures, 2 reconnects, 2.556-second success gap. Abrupt node loss: 2,043 acknowledgements, 282 failures, 278 reconnects, 60.757-second success gap. No acknowledged IDs were missing in these samples; failed operations may have committed and are not replayed. Earlier samples predate the final client TCP user timeout. An initial abrupt-proxy client stalled on unacknowledged TCP data; the final probe uses tcp_user_timeout=5000. [persistent-drain-primary.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/persistent-drain-primary.json) [persistent-node-loss.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/persistent-node-loss.json)

# Observability

**LIVE VALIDATED:** Prometheus Operator, ServiceMonitors, Patroni/PgCat/MinIO/Kubernetes workload scraping; five dashboards loaded in Grafana; 13 panel queries returned actual series. Inventory uses AVAILABLE/MISSING/BROKEN/NOT IMPLEMENTED labels. SQL exporter, API operation metrics, backup-age gauge and logging delivery are absent; several kind control-plane targets refuse connections. This is partial pipeline coverage. [observability-inventory.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/observability-inventory.json) [grafana-loaded-dashboards.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/grafana-loaded-dashboards.json) [dashboard-queries.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/dashboard-queries.json)

# Alerts

**LIVE VALIDATED:** PgCatMetricsUnavailable transitioned inactive → pending → firing → inactive using a real TLS scrape failure, then the ServiceMonitor was restored. The initial NetworkPolicy-only attempt left established connections alive and did not trigger; it is retained under attempts. All six rules loaded/evaluated, but only this one condition was induced. Alertmanager notification delivery is **NOT VALIDATED**. [alert-transitions.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/alert-transitions.json) [prometheus-rules.json](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/prometheus-rules.json)

# Performance Benchmarks

**EXPERIMENTALLY MEASURED:** 24 completed ten-second pgbench samples, scale 1, concurrency 1/10/25/50, direct/PgCat, three profiles; zero reported failed transactions in completed samples. The aborted session-mode attempt is retained separately and excluded. Final pooling mode is transaction. At ten mixed clients: direct 1,318.925 TPS / 7.582 ms mean; PgCat 1,099.301 TPS / 9.097 ms mean. No p95/p99 or reconnect measurements are invented. Single samples, warm caches, shared host and concurrent monitoring checks limit interpretation. [Raw samples](../../results/benchmarks/dbaas-phase5-8a3ad9f385/pgbench.json).

# Failover Under Load

**EXPERIMENTALLY MEASURED:** the node-loss persistent writer is a low-load, single-client transaction stream. A derived JSON reports TPS before the first observed client failure, between first/last failures, and after the last failure. The baseline window is short; these are observed client windows rather than perfectly synchronized injection phases. Zero transaction replay retries; connection reconnections are counted separately. Automatic membership convergence failed. [Window summary](../../results/benchmarks/dbaas-phase5-8a3ad9f385/failover-load.json).

# Backup Impact

**EXPERIMENTALLY MEASURED:** paired 15-second mixed/10-client PgCat samples: no backup 1130.003 TPS / 8.850 ms; concurrent backup 1061.426 TPS / 9.421 ms. Official backup Job completed in 6.205 seconds. CPU/I/O impact was not separately sampled; no causal or production extrapolation. [Raw comparison](../../results/benchmarks/dbaas-phase5-8a3ad9f385/backup-impact.json).

# Recovery Benchmarks

**EXPERIMENTALLY MEASURED:** one 100,000-row payload occupied 119,349,248 bytes (about 113.8 MiB); repeated-md5 content is compressible. Backup Job duration 6.018 seconds; isolated target-time restore plus writable/data checks 16.002 seconds. WAL interval 35,670,400 bytes includes backup/WAL switches. Catalog reports whole-cluster uncompressed/compressed sizes, not payload-only sizes. PITR replay time is not separated from restore time. 500 MiB/1 GiB samples were not run: the selected bounded sample limits disk/WAL growth and this phase prioritized correcting discovered recovery issues. No scaling curve is inferred. [Size sample](../../results/benchmarks/dbaas-phase5-8a3ad9f385/restore-sizes.json).

# Evidence Generated

[Evidence index](../evidence/README.md), [engineering report](../report/engineering-report.md), [executive summary](../report/executive-summary.md), [portfolio material](../portfolio/), 15 Mermaid SVG exports including the ten requested architecture topics, six measured SVG charts and PNG equivalents. [Chart manifest](../images/results/manifest.json). Raw failed attempts remain under runtime/benchmark attempts directories. No fake screenshots or fabricated metrics. [Final checks](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/validation/summary.json).

# Remaining Risks

Automatic replica convergence failed after abrupt loss; corrected-clone abrupt crash behavior remains incomplete; session pooling can reject mixed workload updates after replica selection; MinIO and all workers share one host; volumes are local; replication is asynchronous; benchmark observations are short; some scrape targets are broken. Do not infer a production RPO/RTO from retained sample acknowledgements.

# Production Gaps

Independent failure domains/storage and off-site recovery; fencing/partition drills; TLS; tenant identity/quotas; durable control-plane operations; supported-version/security review; complete SQL/API/backup-age/log instrumentation; more credential classes; repeated performance/recovery measurements and alert notification delivery. These are **NOT VALIDATED**.

## Changed files and design decisions

- `scripts/resilience/`, `kind/resilience.yaml`, `tests/test_phase5.py`: owned-cluster identity guards, bounded experiments, actual metric/benchmark capture and regression checks.
- Both Patroni chart families: configurable archive reads/writes and backup enablement; defaults preserve existing deployments.
- `scripts/isolated-restore.py`, `scripts/object-storage.py`, `scripts/offsite-restore.py`: isolated recovery and provider-neutral Secret-based storage configuration.
- `monitoring/`, `tools/reporting/`, `docs/diagrams/`, `docs/images/`, `results/`: metric-backed dashboards/rules and reproducible evidence/chart sources.
- Root/application READMEs and `docs/{audit,operations,testing,evidence,report,portfolio}`: synchronized implementation, measurements and limitations.

## Validation and cleanup

Baseline: 60 Python tests, six Node test cases plus four readiness cases, six Helm lints, all seven image builds. Final: 69 Python tests, six Node test cases plus four readiness cases, six Helm lints, seven rebuilt images, syntax parsers, npm ci, redacted working-tree/history secret scans. See the linked validation summary for exact final parser counts and cleanup outcome. The owned cluster is deleted and original inotify value restored; unrelated clusters are preserved.
