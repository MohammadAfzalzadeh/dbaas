# Runtime validation summary

Disposable lab evidence only; no production guarantees.

| Check | Status | Details |
|---|---|---|
| baseline | PASS | SQL through PgCat, primary and two replicas; backup objects and WAL |
| isolated_restore | PASS | A present/B absent, target writable; source StatefulSet/PVC identities preserved |
| multinode | PASS | 3 PostgreSQL workers; 2 PgCat replicas; real API provisioning |
| network_policy | PASS | Allowed SQL/replication/backup/API flows and denied unrelated TCP probes |
| setup | FAIL | RuntimeError |
| wal | PASS | Switched segment observed in pg_stat_archiver and object storage |
| pgcat_ha | PASS | Two spread proxies; persistent client through pod deletion |
| disruptions | FAIL | RuntimeError |
