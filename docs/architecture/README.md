# Architecture guide

The diagrams describe implemented components and the tested profile. Chart defaults are smaller: the multi-node lab deliberately enabled three database members and two proxies. All kind nodes share one host; diagram boxes do not establish independent physical failure domains. Source-controlled Mermaid is authoritative for each drawing.

## Diagram catalog

| Topic | Mermaid | SVG | High-resolution PNG |
|---|---|---|---|
| Overall DBaaS | [source](../diagrams/architecture.mmd) | [SVG](../images/architecture/architecture.svg) | [PNG](../images/architecture/architecture.png) |
| Control plane and data plane | [source](../diagrams/control-data-planes.mmd) | [SVG](../images/architecture/control-data-planes.svg) | [PNG](../images/architecture/control-data-planes.png) |
| Provisioning | [source](../diagrams/provisioning-flow.mmd) | [SVG](../images/architecture/provisioning-flow.svg) | [PNG](../images/architecture/provisioning-flow.png) |
| Patroni HA | [source](../diagrams/patroni-ha.mmd) | [SVG](../images/architecture/patroni-ha.svg) | [PNG](../images/architecture/patroni-ha.png) |
| PgCat routing | [source](../diagrams/pgcat-routing.mmd) | [SVG](../images/architecture/pgcat-routing.svg) | [PNG](../images/architecture/pgcat-routing.png) |
| Backup and WAL | [source](../diagrams/backup-wal-path.mmd) | [SVG](../images/architecture/backup-wal-path.svg) | [PNG](../images/architecture/backup-wal-path.png) |
| PITR | [source](../diagrams/pitr.mmd) | [SVG](../images/architecture/pitr.svg) | [PNG](../images/architecture/pitr.png) |
| Isolated restore | [source](../diagrams/isolated-restore.mmd) | [SVG](../images/architecture/isolated-restore.svg) | [PNG](../images/architecture/isolated-restore.png) |
| Restore cutover | [source](../diagrams/restore-cutover.mmd) | [SVG](../images/architecture/restore-cutover.svg) | [PNG](../images/architecture/restore-cutover.png) |
| Multi-node lab | [source](../diagrams/multinode-topology.mmd) | [SVG](../images/architecture/multinode-topology.svg) | [PNG](../images/architecture/multinode-topology.png) |
| Observability | [source](../diagrams/observability.mmd) | [SVG](../images/architecture/observability.svg) | [PNG](../images/architecture/observability.png) |
| Primary failure | [source](../diagrams/failure-recovery.mmd) | [SVG](../images/architecture/failure-recovery.svg) | [PNG](../images/architecture/failure-recovery.png) |
| Node drain | [source](../diagrams/node-drain.mmd) | [SVG](../images/architecture/node-drain.svg) | [PNG](../images/architecture/node-drain.png) |
| Credential rotation | [source](../diagrams/credential-rotation.mmd) | [SVG](../images/architecture/credential-rotation.svg) | [PNG](../images/architecture/credential-rotation.png) |
| NetworkPolicy boundaries | [source](../diagrams/network-boundaries.mmd) | [SVG](../images/architecture/network-boundaries.svg) | [PNG](../images/architecture/network-boundaries.png) |
| Validation architecture | [source](../diagrams/validation-architecture.mmd) | [SVG](../images/architecture/validation-architecture.svg) | [PNG](../images/architecture/validation-architecture.png) |
| Kubernetes HA | [source](../diagrams/kubernetes-ha.mmd) | [SVG](../images/architecture/kubernetes-ha.svg) | [PNG](../images/architecture/kubernetes-ha.png) |
| Graceful shutdown | [source](../diagrams/graceful-shutdown.mmd) | [SVG](../images/architecture/graceful-shutdown.svg) | [PNG](../images/architecture/graceful-shutdown.png) |
| Storage lifecycle | [source](../diagrams/storage-lifecycle.mmd) | [SVG](../images/architecture/storage-lifecycle.svg) | [PNG](../images/architecture/storage-lifecycle.png) |
| Pod failure | [source](../diagrams/pod-failure-flow.mmd) | [SVG](../images/architecture/pod-failure-flow.svg) | [PNG](../images/architecture/pod-failure-flow.png) |

## Design decisions

- **Helm behind FastAPI:** reuses existing chart behavior and keeps operator inputs constrained. Provisioning is synchronous; partial completion is reported and requires operator follow-up.
- **Patroni plus StatefulSets:** Kubernetes supplies identity and placement; Patroni coordinates PostgreSQL roles and replication. Pod readiness alone is insufficient evidence of a healthy database topology.
- **PgCat:** gives clients a connection and routing layer. Multiple endpoints help new connections; established sessions still need application recovery.
- **WAL-G and object storage:** base backups plus archived WAL support target-time recovery. The local MinIO deployment is a lab target, with the same host failure domain.
- **Isolated recovery:** new release and PVC identities preserve the source. Disabling later source-WAL reads and clone archiving separates writable timelines; this does not revoke the clone's mounted storage credentials.
- **Explicit observation boundaries:** promotion, SQL probe success, client recovery and full member convergence are separate measurements.

See the [engineering report](../report/engineering-report.md), [evidence index](../evidence/README.md) and [production gaps](../report/production-gap-analysis.md). Render commands are in [reporting tools](../../tools/reporting/README.md).
