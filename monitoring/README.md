# Monitoring evidence

**LIVE VALIDATED:** five dashboards loaded into Grafana; all 13 panel expressions returned actual series. The initial Phase 5 scrape alert completed inactive/pending/firing/resolved. The continuation later validated four availability/backup conditions across separate rehearsals, while its scrape-fault rerun FAILED to observe pending within the bound. Subsequent harness hardening has static coverage only. See the [current evidence index](../docs/evidence/README.md). Notification delivery is **NOT VALIDATED**.

| Coverage | Inventory classification | Scope |
|---|---|---|
| PostgreSQL process/WAL/member state | AVAILABLE | Patroni metrics; not SQL exporter statistics |
| PostgreSQL connections/locks/database size | NOT IMPLEMENTED | No SQL exporter deployed |
| Patroni roles/streaming/DCS | AVAILABLE | patroni_primary, patroni_postgres_streaming, patroni_dcs_last_seen |
| PgCat transactions/queries | AVAILABLE | pgcat_stats_total_xact_count, pgcat_stats_total_query_count |
| MinIO requests/health | AVAILABLE | minio_api_requests_total and minio_cluster_erasure_set_health |
| Backup Job success/failure | AVAILABLE | kube_job_status_succeeded and kube_job_status_failed |
| Backup age/recoverability | NOT IMPLEMENTED | Job outcomes are not a backup-age or restore proof gauge |
| FastAPI deployment readiness | AVAILABLE | kube_deployment_status_replicas_available |
| FastAPI operations/HTTP latency | NOT IMPLEMENTED | No application metrics endpoint |
| Kubernetes workloads/kubelet | AVAILABLE | Kube-state-metrics and kubelet/cAdvisor targets |
| Kind scheduler/controller/etcd/kube-proxy | BROKEN | Target connections refused; see prometheus-targets.json |
| PVC byte usage | MISSING | No observed kubelet_volume_stats series |
| Loki/Fluent Bit delivery | NOT IMPLEMENTED | No logging stack deployed in this run |

[Raw inventory and targets](../results/runtime/multinode/dbaas-phase5-8a3ad9f385) · [Runbooks](../docs/operations/monitoring-runbooks.md). These AVAILABLE/MISSING/BROKEN/NOT IMPLEMENTED labels describe metric inventory, not broader capability validation.
