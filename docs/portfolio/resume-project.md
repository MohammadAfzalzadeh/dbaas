# Kubernetes-Native PostgreSQL DBaaS Prototype

**One line:** Built and experimentally evaluated a PostgreSQL provisioning platform with FastAPI, Helm, Patroni, PgCat and WAL-G on Kubernetes.

- Built an authenticated FastAPI and browser provisioning path with namespace restrictions, Helm validation, Secret references and explicit partial-failure reporting.
- Designed and validated role-aware PostgreSQL connections, streaming replication and multi-proxy behavior in a disposable Kubernetes lab.
- Implemented and validated isolated target-time recovery with separate PVC identities, source preservation and restored-data checks across graceful and abrupt clone replacement.
- Built persistent-client failure tests that compare acknowledged transaction IDs after node loss; retained failed operations and recovery milestones as separate evidence.
- Corrected backup false-success risk, proxy-watcher termination behavior and stopped-primary alert logic, with regression checks and scoped runtime evidence.
- Measured backup impact at 1,232 → 1,153 TPS in a short paired lab sample; documented the calculated 6.40% reduction and measurement limits.
- Published reproducible architecture sources, measured charts and a failure register retaining an unresolved historical replica anomaly alongside three successful clean reruns.

## Evidence and positioning

[Implementation/validation register](../evidence/README.md) · [backup measurements](../report/performance-results.md#backup-impact) · [failure report](../report/failure-engineering.md).

Use “prototype” and “disposable lab” when discussing scope. Do not convert observed acknowledgement retention into a zero-RPO claim or the measured recovery milestones into an SLA. This package describes repository outcomes; it does not imply a production employer deployment.
