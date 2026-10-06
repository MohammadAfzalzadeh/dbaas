# Project status

“Implemented” describes code or an operator workflow, not a managed service guarantee. PARTIAL production suitability still requires the [gap review](../report/production-gap-analysis.md); the overall platform is NO.

| Capability | Implemented | Validated | Measured | Production-ready? | Known limitation |
|---|---|---|---|---|---|
| API provisioning | YES | LIVE VALIDATED | YES; lab timing | NO | Synchronous operation; no durable reconciliation; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/provisioning.json) |
| Authentication and namespace authorization | YES | STATICALLY VALIDATED | Not separately quantified | NO | Shared operator identity; no tenant authorization; [evidence](../../tests/test_security.py) |
| PostgreSQL / Patroni formation | YES | LIVE VALIDATED | Not separately quantified | NO | One physical host; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/final-topology.json) |
| Streaming replication | YES | LIVE VALIDATED | Not separately quantified | NO | Asynchronous; not universal zero data loss; [evidence](../../results/runtime/patroni/replication.json) |
| PgCat routing | YES | LIVE VALIDATED | Not separately quantified | NO | Not complete SQL routing compatibility; [evidence](../../results/runtime/sql/routing.json) |
| PgCat HA | YES | LIVE VALIDATED | YES; lab timing | NO | Established session can reset; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/proxy-shutdown/attempt-2/result.json) |
| SQL read/write | YES | LIVE VALIDATED | Not separately quantified | NO | Controlled lab dataset; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/baseline.json) |
| Base backup | YES | LIVE VALIDATED | YES; lab timing | NO | Completion alone is not recoverability; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/backup/baseline.json) |
| WAL archival | YES | LIVE VALIDATED | Not separately quantified | NO | Local MinIO shares host failure domain; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/backup/wal.json) |
| In-place PITR | YES | LIVE VALIDATED | YES; lab timing | NO | Explicit destructive workflow; separate from isolated restore; [evidence](../../results/runtime/pitr/result.json) |
| Isolated restore | YES | LIVE VALIDATED | YES; lab timing | NO | Cutover remains an operator decision; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-restore.json) |
| Restart durability | YES | LIVE VALIDATED | YES; lab timing | NO | Single-member clone; no independent disk-loss drill; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json) |
| Primary failover | YES | EXPERIMENTALLY MEASURED | YES | NO | Observed polls, not an RTO guarantee; [evidence](../../results/runtime/failover/primary_failover.json) |
| Replica failure | YES | LIVE VALIDATED | YES; lab timing | NO | Pod deletion differs from partitioned node; [evidence](../../results/runtime/failover/replica_failure.json) |
| Graceful primary drain | YES | EXPERIMENTALLY MEASURED | YES | NO | Node-affine PVC needs original worker; [evidence](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/persistent-drain-primary.json) |
| Graceful replica drain | YES | LIVE VALIDATED | YES; lab timing | NO | Drain timers include blocking command time; [evidence](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/drain-replica.json) |
| Historical abrupt recovery anomaly | PARTIAL | UNRESOLVED | Not separately quantified | NO | UNRESOLVED HISTORICAL FAILURE; NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS; [evidence](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/replica-recovery-diagnostic.json) |
| Clean abrupt node-loss reruns | YES | LIVE VALIDATED | YES; lab timing | NO | Does not prove historical cause fixed; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json) |
| Persistent clients | YES | EXPERIMENTALLY MEASURED | YES | NO | 34 failed transactions; uncertain outcomes not retried; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json) |
| Application credential rotation | YES | LIVE VALIDATED | YES; lab timing | NO | Replication credential rotation NOT VALIDATED; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/rotation-reload/attempt-1/result.json) |
| NetworkPolicy | YES | LIVE VALIDATED | Not separately quantified | NO | Namespace/profile proof, not tenant isolation; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/network-policy.json) |
| Monitoring | YES | LIVE VALIDATED | Not separately quantified | NO | Seven refused targets; instrumentation gaps; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/observability-inventory.json) |
| Admission TLS | YES | LIVE VALIDATED | Not separately quantified | NO | Not end-to-end SQL TLS; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/admission-validation.json) |
| Availability and backup alerts | YES | LIVE VALIDATED | Not separately quantified | NO | See database/proxy attempts too; delivery NOT VALIDATED; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/alert-rehearsal/attempt-3/result.json) |
| Scrape-fault alert rerun | YES | FAILED | Not separately quantified | NO | Later harness hardening is static only; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/metrics-alert/attempt-1/failure.txt) |
| Monitoring harness hardening | YES | STATICALLY VALIDATED | Not separately quantified | NO | No live rerun of this harness revision; [evidence](../../results/validation/monitoring-harness/attempt-1/summary.json) |
| Benchmark matrix | YES | EXPERIMENTALLY MEASURED | YES | NO | Short, single-sample, warm-cache comparisons; [evidence](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/pgbench.json) |
| Backup impact | YES | EXPERIMENTALLY MEASURED | YES | NO | No isolated causal estimate; [evidence](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/backup-impact.json) |
| Restore measurements | YES | EXPERIMENTALLY MEASURED | YES | NO | Compressible payload; scheduling and checks included; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/restore-size/attempt-2/result.json) |
| Image recipes | YES | BUILD VALIDATED | Not separately quantified | NO | No signed registry release or portability guarantee; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/validation/image-builds.txt) |
| Off-site recovery | PARTIAL | NOT VALIDATED | NO | NO | No remote recovery claim; [evidence](../../scripts/offsite-restore.py) |
| Clone replica convergence | Not in tested profile | NOT APPLICABLE | Not separately quantified | NO | Source replica results cannot stand in for clone replicas; [evidence](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/isolated-durability/attempt-1/result.json) |
| Overall DBaaS platform | PARTIAL | Lab-scoped evidence | Lab observations | NO | No production availability or disaster-recovery guarantee |
