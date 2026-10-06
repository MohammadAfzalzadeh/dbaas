# STAR interview stories

These describe repository engineering events, not an employer production incident or independently verified business impact.

## 1. Kubernetes API EOF and host inotify exhaustion

**Situation:** Provisioning could not reliably reach the Kubernetes API despite available credentials.

**Task:** Identify the failure without weakening TLS or granting broad privilege.

**Action:** Compared network, DNS, token/CA and host-resource evidence; found inotify creation failures and kube-proxy initialization errors. Temporarily adjusted the host limit and restarted only owned components.

**Result:** CA-verified Kubernetes access and provisioning passed. The host setting was restored during cleanup; the diagnosis became a documented lab prerequisite.

[Evidence](../audit/phase4-runtime-validation-report.md#kubernetes-api-eof-root-cause)

## 2. Backup false-success risk

**Situation:** Static review found backup target selection and error handling that could allow a misleading success.

**Task:** Make completion mean that a valid primary command actually ran, then verify more than exit status.

**Action:** Added strict selection of a unique primary, authenticated role checking and propagated failures; retained regression coverage and tested official backup Jobs, catalog metadata and restored data.

**Result:** The path now fails on invalid selection and has scoped backup/restore evidence. No historical data loss or production incident is claimed.

[Evidence](../audit/phase1-correctness-report.md)

## 3. PITR and archive separation

**Situation:** An isolated clone later failed checkpoint recovery after worker loss; source archive coupling was unsafe after promotion.

**Task:** Separate bootstrap recovery from subsequent clone history and prove data survives replacement.

**Action:** Disabled later source-WAL reads, clone archive writes and scheduled backups; checked source identities and target-time markers across graceful and abrupt clone replacement.

**Result:** The later clone retained recovered and new rows while excluding later source data. The full original crash cause remains uncertain, and mounted storage credentials remain a separate limitation.

[Evidence](../report/failure-engineering.md)

## 4. Persistent-client failover

**Situation:** A successful new SQL probe could obscure the experience of existing client connections.

**Task:** Measure client failures, acknowledgements and recovery milestones independently.

**Action:** Ran clients outside the failed worker, recorded unique IDs after commit acknowledgement, bounded connection behavior and compared acknowledged IDs after recovery without replaying uncertain operations.

**Result:** The continuation run retained its acknowledged set while recording failed transactions and reconnects. The report distinguishes promotion, probe recovery and client recovery rather than claiming uninterrupted service.

[Evidence](../report/performance-results.md#failover-under-load)

## 5. Historical replica recovery anomaly

**Situation:** The original abrupt-loss test restored a primary but left a replica stuck until manual reinitialization.

**Task:** Investigate and retain evidence while testing whether clean runs reproduce the failure.

**Action:** Captured timeline/WAL diagnostics, restored redundancy explicitly and ran clean automatic-recovery trials with separate artifacts. Avoided rewriting the earlier result after later success.

**Result:** Three later clean runs recovered without reinitialization. The original cause remains unknown: UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS.

[Evidence](../report/failure-engineering.md#the-unresolved-replica-recovery-anomaly)
