# Runtime validation summary

Disposable lab evidence only; no production guarantees.

| Check | Status | Details |
|---|---|---|
| alerts | PASS | Real metrics TLS handshake failure: inactive/pending/firing/resolved; SQL unaffected; ServiceMonitor restored |
| backup_impact | PASS | Paired short pgbench samples; backup completion; no CPU/I/O extrapolation |
| baseline | PASS | SQL through PgCat, primary and two replicas; backup objects and WAL |
| benchmarks | PASS | Stage completed; individual artifacts define the validation scope |
| disruptions | FAIL | RuntimeError |
| drain_primary | PASS | Eviction respected; local PVC member rejoined on original node after uncordon Duration: 109.878 seconds. |
| drain_replica | PASS | Eviction respected; local PVC member rejoined on original node after uncordon Duration: 108.763 seconds. |
| final_sql | PASS | Source deterministic rows on primary, two replicas and PgCat after all experiments |
| isolated_restore | PASS | A present/B absent, target writable; source StatefulSet/PVC identities preserved |
| multinode | PASS | 3 PostgreSQL workers; 2 PgCat replicas; real API provisioning |
| network_policy | PASS | Allowed SQL/replication/backup/API flows and denied unrelated TCP probes |
| observability | PASS | Stage completed; individual artifacts define the validation scope |
| pgcat_abrupt | PASS | Two replicas during abrupt deletion; persistent client outcomes retained |
| pgcat_ha | PASS | Two spread proxies; persistent client through pod deletion |
| proxy_failure | PASS | Stage completed; individual artifacts define the validation scope |
| restore | PASS | Stage completed; individual artifacts define the validation scope |
| restore_size | PASS | One deterministic ~100 MiB sample; larger sizes not run; no scaling curve |
| rotation | PASS | Stage completed; individual artifacts define the validation scope |
| setup | FAIL | RuntimeError |
| upgrades | PASS | OnDelete revision/manual replica-first restart; rolling PgCat and API |
| wal | PASS | Switched segment observed in pg_stat_archiver and object storage |
| cleanup | PASS | Stage completed; individual artifacts define the validation scope |
