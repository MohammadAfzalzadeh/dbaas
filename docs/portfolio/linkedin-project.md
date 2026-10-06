# LinkedIn project package

## Recommended titles

- **GitHub:** Cloud-Native PostgreSQL Database-as-a-Service Platform. Keep “research prototype” in the opening paragraph: the implemented provisioning path justifies DBaaS, while the qualifier sets the right boundary.
- **LinkedIn:** Building and Testing a PostgreSQL DBaaS on Kubernetes. This puts implementation and experimentation at the center.
- **Resume:** Kubernetes-Native PostgreSQL DBaaS Prototype. Compact, technically specific and honest about production maturity.

“Highly Available PostgreSQL Platform on Kubernetes” puts too much weight on HA given the shared physical failure domain and unresolved historical replica anomaly. Prefer the implemented DBaaS workflow and measured failure engineering as the main story.

## A. Short project description

Built a PostgreSQL DBaaS prototype using FastAPI, Helm, Patroni, PgCat, WAL-G and MinIO. Validated provisioning, SQL routing, backup and target-time recovery in disposable Kubernetes labs, then tested node loss, client reconnects, clone durability and credential rotation. Published raw evidence, measured charts and unresolved failures alongside the implementation.

## B. Technical post draft

I started with a PostgreSQL DBaaS on Kubernetes: a browser UI and FastAPI control plane deploying Helm releases, with Patroni for database leadership, PgCat for connections, and WAL-G plus MinIO for backup and WAL storage.

Then I tested what happens when parts of it fail.

In my disposable multi-node lab, I exercised voluntary drains, abrupt worker loss, persistent SQL clients, isolated target-time restores, clone restarts and application credential rotation. All nodes were containers on one host, so the results describe that lab rather than independent host or zone resilience.

The most useful findings were defects:

- Kubernetes API EOF errors traced to host inotify exhaustion and failed kube-proxy initialization.
- Backup error handling could report success without a valid primary target.
- A writable restore clone needed to stop following the source archive after bootstrap.
- A configuration watcher kept a proxy pod alive after PgCat had already exited.
- An alert based only on Patroni's primary role missed a stopped PostgreSQL process.

I corrected those paths and retained regression and runtime evidence. I also kept the failure I cannot yet explain: one historical replica needed manual reinitialization after node loss. Three later clean runs recovered automatically, but that does not establish a root cause or a fix.

Observed during controlled failure testing: four clients acknowledged 20,624 writes, with 34 failed transactions and 19 reconnects; none of the acknowledged IDs were missing afterward. This does not establish zero RPO. [Source](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json).

The paired backup sample measured about 1,232 TPS at baseline and 1,153 TPS during backup, a calculated 6.40% reduction. Those are short shared-host samples, not a capacity guarantee. [Source and methodology](../report/performance-results.md#backup-impact).

The repository includes Mermaid architecture sources, generated charts, raw results, a claims register and production gaps. Seven scrape targets remain broken; off-site recovery, replication credential rotation and notification delivery remain unvalidated.

The main lesson: measure promotion, client recovery and full replica convergence separately—and preserve the evidence that does not fit the success story.

## C. Publishing assets

Use the [ten-slide carousel](linkedin-carousel.md), with architecture and measured charts rather than fabricated dashboard screenshots. Link the repository's actual public URL when publishing; no URL or publication is assumed here. All numbers and claim boundaries are governed by the [claims register](../evidence/claims-register.md).
