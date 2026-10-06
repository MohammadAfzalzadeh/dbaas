# Runtime validation summary

Disposable lab evidence only; no production guarantees.

| Check | Status | Details |
|---|---|---|
| connectivity | PASS | kube-proxy/CoreDNS available; API ready |
| provisioning | PASS |  Duration: 144.213 seconds. |
| postgresql | PASS | Readiness observation after API completion; not total bootstrap time Duration: 0.219 seconds. |
| patroni | PASS | Exactly one primary and one streaming replica; role endpoints match |
| pgcat | PASS | Independent client authenticated through PgCat Service; backend observations recorded |
| sql | PASS | Baseline row matches through PgCat, primary and replica |
| backup | PASS | Official CronJob-derived Job, WAL-G listing and S3 objects verified Duration: 3.238 seconds. |
| wal | PASS | Switched segment observed in pg_stat_archiver and object storage |
| pitr | PASS | A present, B absent, new C write verified on primary/replica/PgCat Duration: 68.532 seconds. |
| primary_failover | FAIL |  |
| replica_failure | NOT RUN |  |
| pgcat_restart | NOT RUN |  |
| backup_during_writes | NOT RUN |  |
| node_drain | NOT RUN |  |
| network_policy | NOT RUN |  |
