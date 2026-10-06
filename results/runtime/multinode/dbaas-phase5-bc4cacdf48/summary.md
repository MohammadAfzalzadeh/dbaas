# Runtime validation summary

Disposable lab evidence only; no production guarantees.

| Check | Status | Details |
|---|---|---|
| backup_impact | PASS | Paired short pgbench samples; backup completion; no CPU/I/O extrapolation |
| baseline | PASS | Stage completed; individual artifacts define the validation scope |
| benchmarks | PASS | Stage completed; individual artifacts define the validation scope |
| isolated_restore | PASS | A present/B absent, target writable; source StatefulSet/PVC identities preserved |
| multinode | PASS | 3 PostgreSQL workers; 2 PgCat replicas; real API provisioning |
| network | PASS | Stage completed; individual artifacts define the validation scope |
| network_policy | PASS | Allowed SQL/replication/backup/API flows and denied unrelated TCP probes |
| observability | PASS | Stage completed; individual artifacts define the validation scope |
| restore | PASS | Stage completed; individual artifacts define the validation scope |
| setup | PASS | Stage completed; individual artifacts define the validation scope |
| wal | PASS | Switched segment observed in pg_stat_archiver and object storage |
| cleanup | PASS | Stage completed; individual artifacts define the validation scope |
