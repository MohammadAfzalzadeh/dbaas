# Phase 5 execution plan

Preserve Phase 4 evidence and all uncommitted source. Baseline: 60 Python tests, 10 JavaScript checks, six Helm lints and seven local image builds pass before changes.

| Experiment | Requirement | Execution boundary |
|---|---|---|
| Multi-node provisioning / three Patroni members | REQUIRED | One control plane, three workers; strict worker anti-affinity; local-path volumes. |
| Two PgCat replicas / persistent SQL | REQUIRED | Independent client, committed-ID ledger, reconnect/failure measurements. |
| Replica and primary worker drain / PDB | REQUIRED | Eviction API, bounded timeout, no force or eviction bypass. Local volumes may prevent relocation until node return. |
| Abrupt worker stop/start | OPTIONAL | Task-owned kind worker only; separate from graceful drain. |
| Enforcing NetworkPolicy | REQUIRED | Pinned Calico installation; positive and negative probes. |
| Isolated target-time restore | REQUIRED | New release/PVCs, source unchanged, separate archive destination or archiving disabled on target. |
| External S3 configuration / harness | REQUIRED | External Secret, TLS endpoint, region/path-style options; no public-cloud credentials in CI. |
| Off-site restore | OPTIONAL | Requires actual external target; otherwise NOT VALIDATED. A second local MinIO is not off-site evidence. |
| Credential rehearsal / controlled restarts | REQUIRED | Disposable credentials, old-password rejection, coordinated restart limits. |
| Observability / alerts | REQUIRED | Scrape actual endpoints; inventory unavailable exporters; safe alert transitions. |
| pgbench direct/proxy and three profiles | REQUIRED | Identical small dataset/duration, concurrency 1/10/25/50 if safe; raw output retained. |
| Failover workload / backup impact | REQUIRED | Modest load, transaction outcomes and interruption samples. |
| Recovery size series | OPTIONAL | Bounded datasets; host disk/memory checks. |
| Production cutover / major PG upgrade | NOT APPLICABLE | Design only; no production endpoint changes or unsupported major upgrades. |

Artifacts belong under `results/runtime/multinode` and `results/benchmarks`; existing Phase 4 results remain untouched. Every major claim uses an explicit validation classification. Restore, drain and host changes are bounded to the owned lab, with cleanup in the harness and a separate cleanup command after staged development.
