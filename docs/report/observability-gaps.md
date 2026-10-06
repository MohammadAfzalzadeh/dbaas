# Observability gaps

The continuation inventory records seven broken scrape targets. The observed transport error is **connection refused**. That establishes failure to reach a listener; the precise component binding/exposure configuration was not established in this run. Do not attribute these failures to credentials or TLS without new evidence.

| Job/component | Endpoint | Observed error |
|---|---|---|
| kube-controller-manager | `https://172.21.0.8:10257/metrics` | Connection refused |
| etcd | `http://172.21.0.8:2381/metrics` | Connection refused |
| kube-proxy | `http://172.21.0.8:10249/metrics` | Connection refused |
| kube-proxy | `http://172.21.0.5:10249/metrics` | Connection refused |
| kube-proxy | `http://172.21.0.6:10249/metrics` | Connection refused |
| kube-proxy | `http://172.21.0.7:10249/metrics` | Connection refused |
| kube-scheduler | `https://172.21.0.8:10259/metrics` | Connection refused |

[Exact target inventory and errors](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/observability-inventory.json)

Patroni, PgCat, MinIO and Kubernetes workload metrics support the existing dashboards. There are five provisioned dashboards with thirteen inventoried query expressions; these are actual metric queries, not fabricated screenshots. SQL connection/lock instrumentation, provisioning operation metrics, backup-age/recovery-chain monitoring and centralized log delivery remain incomplete or absent. [Dashboard source](../../monitoring/grafana/).

Availability and backup conditions completed live alert transitions across separate rehearsals. Notification delivery is NOT VALIDATED. The later scrape-fault attempt failed to observe pending within its bound; subsequent harness changes have regression tests only. Neither a working dashboard nor a Job-success metric establishes database recoverability. [Claim scope](../evidence/README.md).

## Follow-up criteria — Planned

Inspect listeners and scrape configuration inside a future owned lab, retain evidence for each endpoint, and demonstrate sustained successful scrapes. Add instrumentation only with defined collection paths and tested queries. Exercise notification routing independently from rule evaluation. Rehearse the hardened harness before changing its classification to LIVE VALIDATED.
