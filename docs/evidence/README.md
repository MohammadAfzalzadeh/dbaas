# Authoritative evidence index

Start here for the validation boundary of every public claim. [Claims register](claims-register.md) controls allowed wording; [project status](project-status.md) distinguishes implementation from production suitability; [final validation](final-validation-summary.md) separates current static/build checks from historical live runs.

## Environments

- **Phase 4:** single-node kind, two database members and one PgCat; default CNI does not prove NetworkPolicy enforcement. [Environment](../../results/runtime/environment.json).
- **Initial Phase 5:** `dbaas-phase5-8a3ad9f385`, one control-plane container and three workers, three database members, two proxies, Calico and local-path storage. [Environment](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/environment.json).
- **Phase 5 continuation:** `dbaas-phase5-bc4cacdf48`, same topology class, new clean lab and independent artifacts. [Environment](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/environment.json).
- **Phase 6:** packaging and local validation only; no new live failure or performance run. Dates shown in historical artifacts remain unchanged. The final package is dated 2026-10-04 in the client's Asia/Tehran time zone.

All kind nodes share one physical host. A dirty working tree is recorded; the commit hash alone is insufficient to reproduce it. Raw PASS/FAIL labels remain historical; the classifications below describe claim scope.

## Capability register

| Capability | Validation classification | Environment | Evidence path | Measured result / observation | Limitations |
|---|---|---|---|---|---|
| API provisioning | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/provisioning.json) | Authenticated deployment completed in 171.647 s | Synchronous operation; no durable reconciliation |
| Authentication and namespace authorization | STATICALLY VALIDATED | Unit/middleware tests | [evidence](../../tests/test_security.py) | Bearer guard and namespace rejection regressions | Shared operator identity; no tenant authorization |
| PostgreSQL / Patroni formation | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/final-topology.json) | One primary and two streaming replicas | One physical host |
| Streaming replication | LIVE VALIDATED | Phase 4 | [evidence](../../results/runtime/patroni/replication.json) | Replica SQL and streaming state checked | Asynchronous; not universal zero data loss |
| PgCat routing | LIVE VALIDATED | Phase 4 | [evidence](../../results/runtime/sql/routing.json) | Primary and replica read backends observed | Not complete SQL routing compatibility |
| PgCat HA | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/proxy-shutdown/attempt-2/result.json) | Peer endpoint stayed ready; replacement observed at 2.349 s | Established session can reset |
| SQL read/write | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/baseline.json) | Deterministic rows through SQL path | Controlled lab dataset |
| Base backup | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/backup/baseline.json) | CronJob-derived Job and WAL-G catalog checked | Completion alone is not recoverability |
| WAL archival | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/backup/wal.json) | Switched WAL segment observed in object storage | Local MinIO shares host failure domain |
| In-place PITR | LIVE VALIDATED | Phase 4 | [evidence](../../results/runtime/pitr/result.json) | A retained, B excluded, new C writable | Explicit destructive workflow; separate from isolated restore |
| Isolated restore | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-restore.json) | New release/PVCs; source preserved | Cutover remains an operator decision |
| Restart durability | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json) | A/C retained; B/future D excluded after both replacements | Single-member clone; no independent disk-loss drill |
| Primary failover | EXPERIMENTALLY MEASURED | Phase 4 | [evidence](../../results/runtime/failover/primary_failover.json) | Promotion 25.171 s; SQL probe 25.370 s | Observed polls, not an RTO guarantee |
| Replica failure | LIVE VALIDATED | Phase 4 | [evidence](../../results/runtime/failover/replica_failure.json) | Replica rejoined; acknowledged IDs retained | Pod deletion differs from partitioned node |
| Graceful primary drain | EXPERIMENTALLY MEASURED | Initial Phase 5 | [evidence](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/persistent-drain-primary.json) | 2 failed transactions; longest success gap 2.556 s | Node-affine PVC needs original worker |
| Graceful replica drain | LIVE VALIDATED | Initial Phase 5 | [evidence](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/drain-replica.json) | Eviction/PDB path and node return exercised | Drain timers include blocking command time |
| Historical abrupt recovery anomaly | UNRESOLVED | Initial Phase 5 | [evidence](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/replica-recovery-diagnostic.json) | Initial FAILED; manual reinitialize restored replica | UNRESOLVED HISTORICAL FAILURE; NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS |
| Clean abrupt node-loss reruns | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json) | Three automatic rejoin runs without reinitialize | Does not prove historical cause fixed |
| Persistent clients | EXPERIMENTALLY MEASURED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json) | Four-client run: 20,624 acknowledged; none missing | 34 failed transactions; uncertain outcomes not retried |
| Application credential rotation | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/rotation-reload/attempt-1/result.json) | New accepted, old rejected; held sessions continued | Replication credential rotation NOT VALIDATED |
| NetworkPolicy | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/network-policy.json) | Calico allowed intended flows and denied probes | Namespace/profile proof, not tenant isolation |
| Monitoring | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/observability-inventory.json) | Actual metric inventory and five dashboards | Seven refused targets; instrumentation gaps |
| Admission TLS | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/admission-validation.json) | Invalid rule rejected with fail-closed CA-backed admission | Not end-to-end SQL TLS |
| Availability and backup alerts | LIVE VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/alert-rehearsal/attempt-3/result.json) | Four conditions completed transitions across attempts 1–3 | See database/proxy attempts too; delivery NOT VALIDATED |
| Scrape-fault alert rerun | FAILED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/metrics-alert/attempt-1/failure.txt) | Pending not observed within bound | Later harness hardening is static only |
| Monitoring harness hardening | STATICALLY VALIDATED | Follow-up tests | [evidence](../../results/validation/monitoring-harness/attempt-1/summary.json) | 79 Python tests, including five new failure-path cases | No live rerun of this harness revision |
| Benchmark matrix | EXPERIMENTALLY MEASURED | Phase 5 continuation | [evidence](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/pgbench.json) | 24 complete samples; zero reported failed transactions | Short, single-sample, warm-cache comparisons |
| Backup impact | EXPERIMENTALLY MEASURED | Phase 5 continuation | [evidence](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/backup-impact.json) | 1231.640 → 1152.865 TPS; derived change −6.40% | No isolated causal estimate |
| Restore measurements | EXPERIMENTALLY MEASURED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/restore-size/attempt-2/result.json) | 113.8 / 500.7 MiB: 15.181 / 16.499 s | Compressible payload; scheduling and checks included |
| Image recipes | BUILD VALIDATED | Phase 5 continuation | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/validation/image-builds.txt) | Seven local builds | No signed registry release or portability guarantee |
| Off-site recovery | NOT VALIDATED | Configuration only | [evidence](../../scripts/offsite-restore.py) | Helper exists; no external target evidence | No remote recovery claim |
| Clone replica convergence | NOT APPLICABLE | One-member restore profile | [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json) | No clone replica in this test | Source replica results cannot stand in for clone replicas |

## Attempt history and supporting detail

The historical replica failure is **UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS**. Initial result: **FAILED**. Three later successful clean runs do not establish a root cause or justify “fixed.”

- [Failure engineering report](../report/failure-engineering.md): symptoms, causes, remediation and residual uncertainty.
- [Phase 4 attempt history](../../results/runtime/attempts/README.md): failed setup and intermediate lifecycle attempts.
- [Detailed continuation artifact index](phase5-continuation.md): supporting paths, not an alternative claim authority.
- [Proxy alert](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/alert-rehearsal/attempt-1/result.json), [database/leader alerts](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/alert-rehearsal/attempt-2/result.json), [backup alert](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/alert-rehearsal/attempt-3/result.json).
- [Smaller restore sample](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/restore-size/attempt-1/result.json) accompanies the larger sample above.
- [Performance report](../report/performance-results.md): full matrix and exact measurement semantics.

Historical artifacts are preserved. No failed attempt is included in a later successful count, and no local measurement establishes an SLA, production RPO or RTO.
