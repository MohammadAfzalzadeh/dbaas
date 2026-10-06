# Production gap analysis

These are gates for a proposed production deployment, not a demand that a research prototype implement every enterprise feature. Priority depends on workload, tenancy and agreed recovery objectives. The overall platform remains **NO** for production readiness; individual mechanisms may be **PARTIAL**. [Status matrix](../evidence/project-status.md).

## CRITICAL BEFORE PRODUCTION

| Gap | Current boundary | Required decision / acceptance evidence |
|---|---|---|
| Independent failure domains and storage | kind workers and local MinIO share one host; local-path PVCs are node-affine | Choose storage and placement with documented loss/attachment semantics; test host, disk and zone failures without deleting data to force recovery |
| Off-site backups and disaster recovery | External endpoint/helper exists; execution NOT VALIDATED | Restore from independent object storage into a fresh cluster; verify data, WAL retention, encryption, access isolation and recovery timing |
| Unresolved replica anomaly | Initial FAILED; three later clean automatic recoveries | Retain risk and manual recovery runbook; obtain reproducer/root-cause evidence or explicitly accept bounded residual risk before relying on automation |
| TLS and identity boundaries | Operator Bearer token, scoped RBAC and Secret references; no end-to-end trust proof | Authenticate API/SQL/object-store transport, issue/rotate trust material, verify certificate failure behavior and least privilege |
| Recovery objectives | No established production SLO, RPO or RTO | Define user-visible SLIs, durability expectations and recovery milestones; measure against representative failure and load conditions |
| Tenant isolation, if offered as shared DBaaS | Namespace allowlist is not tenant identity or SQL authorization | Design tenant authentication/authorization, resource ownership, quotas, audit trail and isolation tests before onboarding untrusted tenants |

## HIGH PRIORITY

| Gap | Current boundary | Planned acceptance criterion |
|---|---|---|
| API/control-plane HA | Synchronous request-bound Helm calls | Durable operation records, idempotency, ownership-aware locking and safe recovery after API restart |
| Reconciliation | No continuous control loop | Detect drift and retry safely without overwriting operator decisions; consider an Operator with explicit status conditions |
| PgCat HA defaults | Lab used two proxies; defaults smaller | Choose production replica/placement and disruption settings; test existing client reconnect behavior |
| Credential lifecycle | Application role/PgCat reload exercised | Validate replication, administrative and object-store rotation, overlapping credentials where needed, rollback and revocation; held sessions are a separate policy |
| Observability | Seven refused scrape targets; SQL/API/backup-age gaps | Repair listeners/scrape paths, instrument operations and archive health, validate rules and actual notification delivery |
| Release and upgrades | Local images build; no signed release lifecycle | Pin and review supported versions, scan dependencies/images, publish immutable artifacts, test rollback and rolling upgrades |
| PostgreSQL major upgrades | NOT VALIDATED | Choose upgrade method, rehearse data compatibility, application cutover and rollback using representative datasets |
| Repeat disaster-recovery drills | Local target-time restores only | Scheduled, independently observed drills, retained evidence and actionable response runbooks |

## MEDIUM

| Gap | Planned work |
|---|---|
| Capacity planning | Repeat longer tests on representative data and concurrency; measure latency distributions, saturation, storage and cache effects |
| Pool sizing and workload compatibility | Budget connections across replicas and operational clients; validate session-dependent features and routing consistency |
| Alert quality and operational ownership | Set escalation ownership, silence/maintenance handling and symptom-based SLO alerts; distinguish database health from process role |
| Audit and retention | Retain authenticated operation history; define backup/log/evidence retention and deletion controls |
| Reproducibility | Capture dependency and image digests, source manifest and host configuration; current historical Git revision records a dirty tree |

## OPTIONAL

A richer self-service UI, billing, organization management, automated clone cutover and broader cloud-provider support are future product choices. They should follow a defined user need. They are not implied by the current DBaaS prototype title.

## Exit principle

Promote a claim only when the acceptance evidence exists. Successful retries do not erase failed history; static tests do not substitute for live operations; one short lab sample does not establish an availability or recovery guarantee. [Claims register](../evidence/claims-register.md).
