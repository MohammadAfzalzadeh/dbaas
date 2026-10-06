# Monitoring scope and response

The [rules](../../monitoring/prometheus/rules.yaml) use real metric families captured in the Phase 5 lab. Change the Prometheus release label and namespace for your deployment. Set runbook URLs to your published documentation location before sharing alerts externally. This lab does not configure notification delivery.

| Alert | First response | Interpretation limit |
|---|---|---|
| PostgreSQLProcessUnavailable | Inspect the selected member's Patroni status, pod conditions and PostgreSQL startup errors. Compare healthy replicas before any restart. | No series is different from a reported zero; inspect scrape health too. |
| PatroniNoLeader | Inspect all members and DCS/API reachability. Confirm whether writes succeed through the primary Service. | Does not detect a completely absent metric family; do not promote manually based on this alert alone. |
| PatroniReplicaNotStreaming | Compare timeline, replay LSN and archive recovery state. Inspect WAL availability. | Archive recovery can be legitimate. The Phase 5 lagging replica required explicit reinitialization. |
| PgCatUnavailable | Inspect proxy Deployment readiness and SQL probes, then endpoints and rollout state. | Measures available replicas, not a client latency SLO. |
| PgCatMetricsUnavailable | Check endpoint readiness, NetworkPolicy and metrics port 9930. Probe SQL independently. | A scrape failure does not prove SQL is unavailable. |
| BackupJobFailed | Inspect Job conditions and sanitized logs, then WAL-G catalog and the archived WAL chain. | Failed pod count can coexist with eventual retry success. Job success does not prove restore correctness. |
| ControlPlaneReplicaUnavailable | Check the API Deployment, image availability and Kubernetes API connectivity. | Available replicas do not prove an authenticated provisioning operation succeeds. |

## Missing coverage

No SQL exporter is deployed: database connections, locks, sizes and PostgreSQL transaction counters are not claimed as Prometheus series. PgCat transaction counters describe the proxy only. No backup-age gauge, restore-duration exporter, API operation histogram, or proven PVC byte-usage series is supplied. `BackupTooOld`, database replication-byte lag and `PVCUsageHigh` remain Planned until trustworthy instrumentation and thresholds exist. Loki/Fluent Bit scraping is NOT VALIDATED in this run.

## Safe alert rehearsal

`scripts/resilience/monitoring-checks.py` loads dashboards, queries their expressions and applies the rules. It temporarily configures HTTPS against the disposable PgCat plaintext metrics port, producing a real TLS scrape failure. SQL is unchanged. It polls inactive → pending → firing, restores the original ServiceMonitor in a `finally` block, then requires inactive (resolved). No metric values are injected. The first attempt removed metrics NetworkPolicy ingress, but existing connections continued; that unsuccessful transition remains in `attempts/alert-existing-connections/`. An interrupted host process can bypass `finally`; inspect or remove the task-owned cluster before reuse.

The two-minute delay follows the rule's `for` period. A scrape timeout and evaluation interval add latency. [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) define pending and firing semantics. Other alert conditions are not automatically claimed as live-triggered because one rule passes.

## Member discovery

Upgrade Patroni charts and `serviceMonitor/patroni-service.yaml` together. The dedicated `pgmetrics-<release>` Service publishes unready members on port 8008 only, so a stopped PostgreSQL process can still report its state. SQL Services retain role and readiness filtering.

The continuation's `alert-rehearsal.py` also exercises zero available proxies, PostgreSQL stopped under paused Patroni on an isolated clone, and a real backup Job that finds no primary. The leader expression combines role and process-running metrics because a paused stopped primary can retain its primary role metric. `tests/prometheus_rules_test.yaml` covers that case and a healthy control. Backup Job evidence uses `Never` restart policy to retain the failed pod for log capture. Each workload is restored after its fault; notification delivery remains NOT VALIDATED.
