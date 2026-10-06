# Interview talking points

Use these as technical explanations, with claim scope from the [evidence index](../evidence/README.md). Answers describe the current prototype; redesign ideas are explicitly Planned.

## Why Patroni instead of a StatefulSet alone?

A StatefulSet supplies stable identities and volume associations. It does not decide which PostgreSQL instance may be writable, configure replication or orchestrate promotion. Patroni adds database-aware role management through Kubernetes DCS state. Both layers matter: the drain experiments showed that correct leadership does not make a local PVC portable.

## How does leader election work?

Members coordinate through Kubernetes DCS state and leadership ownership. A member needs the appropriate leadership state and database eligibility before promotion; observed roles then drive Service routing. The harness polls leadership rather than instrumenting every internal election step, so reported promotion time includes observation delay.

## How does Patroni prevent split brain?

Leadership ownership, refresh/demotion behavior and replica eligibility are core mechanisms. Their safety still depends on DCS behavior and partition/fencing assumptions. This repository has not proven all network-partition, process-pause or storage-loss cases. I would review effective Patroni settings and test both sides of a partition before making a split-brain guarantee; a PDB or a Service label cannot supply that proof.

## What happens when the primary node disappears?

The remaining members can promote an eligible replica and routing follows the new role. Existing connections may fail until client timeouts and reconnects complete. The returned worker also has to converge onto the current history. One original run restored SQL but failed replica convergence; three clean later runs converged without reinitialization. These are different outcomes within the same broad fault category.

## Why did one historical replica fail to recover?

The exact trigger is unknown. Diagnostics captured a request for WAL position 0/14000000 on timeline 4 while the primary flush position was 0/130799C8. That explains why the state deserved investigation, but does not establish how it arose. Manual reinitialization restored the member; it is remediation, not a root-cause fix.

## What do you know and not know about that failure?

I know the initial automatic convergence failed, the diagnostic positions differed and reinitialization restored redundancy. I know three later clean runs converged automatically. I do not know the precise preceding transition or whether a particular timing, timeline or archive interaction was necessary. The honest classification is UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS.

## Why PgCat?

It supplies a connection-pooling and role-routing layer while letting the control plane expose a consistent endpoint. The project measures its costs and failure behavior instead of assuming throughput improvement. An early mixed workload exposed session-pooling behavior when a read-first session later attempted a write; the final benchmark deliberately uses transaction pooling.

## What happens when PgCat dies?

A Service with a healthy peer can send new connections to that peer. Existing TCP sessions on the lost pod do not move and may fail. The client must reconnect and decide what to do with uncertain transactions. Shutdown testing also found that the watcher could outlive PgCat; bounded signal handling fixed that container-lifecycle defect without shortening the database client drain grace.

## How were acknowledged writes validated?

Each client writes a unique ID and records it only after commit acknowledgement. After recovery, the harness compares those IDs with database rows. This establishes retention of the observed acknowledgement set. It does not establish that every failed transaction rolled back; a connection can fail after commit but before the acknowledgement reaches the client, so uncertain transactions are not silently retried.

## Promotion time versus client recovery time?

Promotion is when a new primary is observed. SQL recovery is a separate probe becoming usable. A held client may recover later because it is waiting on a stale TCP connection, pool backend or timeout. Full member convergence is later still. The performance report labels these boundaries and notes that client errors can continue after the independent probe succeeds.

## How does WAL archiving work?

PostgreSQL generates WAL and the configured archive path uses WAL-G to send completed segments to object storage. The test forces a segment switch and checks both archiver progression and the segment object. That verifies the tested path; completeness for a future restore target also depends on retention, continuity and available base backups.

## How does PITR work?

Choose a base backup completed before the requested UTC target, restore it and replay the necessary archived WAL until the target before promotion. The meaningful test is data semantics: a before-target marker exists, a later marker is absent and a new write succeeds. Backup-command exit status alone cannot demonstrate that.

## Why did isolated restore remain coupled to source WAL?

Bootstrap needed source WAL, but the earlier configuration continued exposing a source restore command during later recovery. A writable clone develops its own history, making later source reads unsafe. The original clone checkpoint failure motivated the correction; complete causality for that crash is not claimed.

## How was archive separation corrected?

The clone reads source archives during bootstrap, then disables subsequent source recovery reads, archive writes and scheduled backups. The durability test checks recovered rows and clone writes after graceful and abrupt replacements while excluding later source-only data. Credentials are still mounted, so configuration separation is not equivalent to IAM revocation.

## Why is isolated restore operationally safer than in-place restore?

A new release and new PVC identities preserve the source for comparison and rollback. Ownership checks reject an existing target, reducing accidental overwrite risk. It still consumes resources and needs a deliberate write boundary, endpoint cutover and rollback decision. In-place recovery remains a separate destructive workflow with explicit execution controls.

## How does backup affect performance?

The final paired sample recorded lower TPS and higher mean latency while the official backup Job ran. The reporting script calculates the relative TPS change from raw data. Shared CPU/storage, cache state and short sampling mean the result is an observed association, not a universal backup overhead estimate. See the performance report for values and retained resource counters.

## What does the benchmark prove?

It records completed transactions, TPS and mean latency for the exact direct/proxy routes, workload scripts, concurrency and configuration used in that lab. It also exposed a workload/pooling mismatch before the final run. The completed matrix supports transparent comparisons within the recorded environment.

## What doesn't the benchmark prove?

It does not establish production capacity, percentile latency, statistical significance, cold-cache behavior, a general scaling curve or that PgCat is faster. Each point is a single short small-dataset sample. Missing percentile and reconnect measurements stay null rather than being inferred.

## What caused the Kubernetes API EOF problem?

Diagnostics showed host inotify exhaustion, failing kube-proxy initialization and unhealthy DNS. Token and CA availability did not explain the failure. Temporarily increasing the host limit and restarting only owned components restored CA-verified Kubernetes access. The evidence supports this diagnosis for that environment; it is not a rule that every EOF has the same cause.

## Why did inotify exhaustion affect kube-proxy?

The host limit constrained creation of inotify instances used by containerized processes. A fresh diagnostic process returned errno 24 even with few ordinary descriptors, and kube-proxy logs reported initialization failure. That disrupted Service networking and coincided with unhealthy DNS. Raising the relevant host limit, rather than merely changing a process file-descriptor setting, restored the tested path.

## What are current single points of failure?

The physical lab host and local MinIO are shared failure domains. The API workflow has no durable operation service or proven multi-replica coordination. Default PgCat replica count is smaller than the HA test profile. Node-affine storage can leave a member unavailable until its worker returns. A production assessment must consider Kubernetes control-plane and storage topology beyond the kind diagram.

## What remains before production?

Independent storage/failure domains, verified off-site restore, explicit TLS/identity boundaries, durable operations, a supported upgrade strategy, complete observability and alert delivery, and workload-specific objectives. The replica anomaly needs resolution or explicit residual-risk handling. Shared DBaaS additionally requires tenant authorization and quotas. The gap analysis ranks these gates.

## How would you redesign this using an Operator?

Planned: define a database CRD with topology, Secret references and storage policy, plus status conditions and observed generation. Reconcile idempotently with ownership checks and durable progress rather than depending on a request remaining alive. Separate destructive recovery into an explicit operation resource with immutable source/target identities. Introduce concurrency controls and upgrade state transitions before adding automation.

## How would you support multi-tenancy?

Planned: authenticate individual tenant identities, authorize every operation against resource ownership, enforce quotas and constrain database roles, namespaces, network and storage access. Keep operator privilege separate from tenant requests and record an audit trail. Namespace allowlisting and a shared Bearer token are useful operator controls but insufficient tenant isolation.

## How would you design off-site disaster recovery?

Planned: write or replicate backups/WAL into an independently administered failure domain with explicit retention, encryption and least-privilege credentials. Restore into a fresh cluster that does not depend on source-local storage, assert target-time data and record all milestones. Test missing WAL, credential failure and retention errors too. The existing external helper is configuration capability; external recovery remains NOT VALIDATED.

## How would you define RPO and RTO?

Start with the application durability and availability contract. Define which acknowledged writes may be lost, which failure domain is covered and which service milestone ends recovery. Measure replication/archive lag and restore completeness for RPO; measure detection, promotion or restore, routing and application recovery for RTO. Report distributions across realistic repeated drills rather than selecting a favorable lab point.

## Do current numbers represent an SLA?

No. They are observations in a disposable shared-host environment with explicit workloads and probe boundaries. An SLA needs an agreed service definition, measurement window and operational commitment. This project has no established numerical production availability, RPO or RTO promise.

## Source map

- Leadership, clients, replica anomaly and clone separation: [failure engineering](../report/failure-engineering.md), with linked raw experiments.
- Throughput, backup cost and timing semantics: [performance report](../report/performance-results.md).
- API EOF and host limits: [Phase 4 diagnosis](../audit/phase4-runtime-validation-report.md#kubernetes-api-eof-root-cause).
- Current identity/provisioning implementation: [application README](../../application/README.md).
- Operator, tenancy, off-site and objective design: [production gaps](../report/production-gap-analysis.md); these are future decisions.
