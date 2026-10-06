# Runtime validation summary

Disposable lab evidence only; no production guarantees.

| Check | Status | Details |
|---|---|---|
| backup | PASS | Official CronJob-derived Job, WAL-G listing and S3 objects verified Duration: 3.558 seconds. |
| backup_during_writes | PASS | Concurrent writes and backup completion verified; restore of this second backup NOT RUN |
| connectivity | PASS | kube-proxy/CoreDNS available; API ready |
| network_policy | NOT APPLICABLE | Default kind CNI does not enforce policy; policies remain disabled |
| node_drain | NOT APPLICABLE | Single-node kind; no multi-worker drain model |
| patroni | PASS | Exactly one primary and one streaming replica; role endpoints match |
| pgcat | PASS | Independent client authenticated through PgCat Service; backend observations recorded |
| pgcat_restart | PASS | Prior committed test rows verified; new write and stable membership verified Duration: 4.057 seconds. |
| pitr | PASS | A present, B absent, new C write verified on primary/replica/PgCat Duration: 77.734 seconds. |
| postgresql | PASS | Readiness observation after API completion; not total bootstrap time Duration: 0.209 seconds. |
| primary_failover | PASS | Prior committed test rows verified; new write and stable membership verified Duration: 22.716 seconds. |
| provisioning | PASS |  Duration: 144.191 seconds. |
| replica_failure | PASS | Prior committed test rows verified; new write and stable membership verified Duration: 22.699 seconds. |
| sql | PASS | Baseline row matches through PgCat, primary and replica |
| wal | PASS | Switched segment observed in pg_stat_archiver and object storage |
