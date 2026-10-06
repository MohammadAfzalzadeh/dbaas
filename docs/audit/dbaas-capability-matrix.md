# DBaaS capability matrix

> Phase 6 navigation: this document retains its historical audit scope. For current classifications and remaining risks, use the [authoritative evidence index](../evidence/README.md) and [production gap analysis](../report/production-gap-analysis.md).

Continuation results: [Phase 5 follow-up](phase5-continuation-report.md). Historical failed outcomes below remain preserved; see the follow-up for current validation scope.

Baseline audit: 2026-10-01; Phase 4 update: 2026-10-03. Source revision: `c275fc2dd3c4e8e9db1e28eadf50100e3cfcbbc1`.

This matrix describes the checked-in implementation, not a certified running service. **IMPLEMENTED** means a complete code path exists for the stated narrow operation; it does not mean that an integration test passed. **PARTIALLY IMPLEMENTED** means meaningful plumbing exists but defects, missing steps, or missing lifecycle semantics prevent treating the operation as complete. **NOT IMPLEMENTED** means no product operation was found. Operator access to Helm, kubectl, or an upstream tool is not automatically an application capability.


Phase 1 update (2026-10-01): current behavior below incorporates locally validated correctness changes. No live cluster was used. See the [Phase 1 report](phase1-correctness-report.md); implementation status does not imply production readiness.

## Validation evidence

Implementation status and validation status are separate. **STATICALLY VALIDATED** means source/render/unit checks; **BUILD VALIDATED** means a successful image build; **SMOKE VALIDATED** means a real provisioning integration; **LIVE VALIDATED** means the stated operation was exercised against live data. **NOT VALIDATED** means there is no runtime proof for that capability. None is a production certification. See the [Phase 4 report](phase4-runtime-validation-report.md) and [runtime evidence](../../results/runtime/summary.md) for exact scope and failed attempts.

## Lifecycle and configuration

| Capability | Status | Validation | Implementation and evidence | Boundary / missing behavior |
|---|---|---|---|---|
| Serve browser provisioning form | IMPLEMENTED | STATICALLY VALIDATED | [`main.py`](../../application/app/main.py), `home()`; [`index.html`](../../application/static/index.html) | One initialization/submit path is tested with a stub DOM; real browser integration remains untested. |
| Submit a deployment through HTTP | IMPLEMENTED | SMOKE VALIDATED | `POST /api/deploy`, `DeploySpec`, `deploy()`, `run()` in `main.py`; UI `handleSubmit()` | Synchronous request returns a bounded Helm completion summary. No durable operation ID. |
| Create PostgreSQL cluster | PARTIALLY IMPLEMENTED | SMOKE VALIDATED | `deploy()` → `patroni-values.yaml.j2` → Helm `upgrade --install` → application Patroni StatefulSet | Default namespaced permissions and dependent names corrected; namespace/RoleBinding must be pre-provisioned. Real API creation passed in disposable kind with two PostgreSQL members; see Phase 4 evidence. |
| Delete cluster | NOT IMPLEMENTED | NOT VALIDATED | No DELETE route or product deletion flow | Recovery script uninstalls releases, but that is a destructive operator recovery procedure, not a cluster deletion API. |
| List clusters | NOT IMPLEMENTED | NOT VALIDATED | No list route, inventory model, or UI list | Helm records exist in Kubernetes; the application never lists them. |
| Retrieve cluster status | NOT IMPLEMENTED | NOT VALIDATED | `/healthz` only returns `{"ok": true}` | Helm `--wait` checks deployment progress, not a persistent cluster status endpoint. |
| Retrieve connection information | NOT IMPLEMENTED | NOT VALIDATED | `deploy()` returns only `ok`, `release`, `namespace`, `output` | No hostname/port/TLS/user/connection-string contract; users must derive Service names. |
| Select namespace | PARTIALLY IMPLEMENTED | SMOKE VALIDATED | `DeploySpec.namespace`, UI field, `--namespace` argument | Default dbaas; explicit operator namespace allowlist plus Kubernetes RoleBinding required. Backend cannot create Namespaces. |
| Configure replica count on creation | IMPLEMENTED | SMOKE VALIDATED | `Postgres.pgReplicas` → [`patroni-values.yaml.j2`](../../application/app/templates/patroni-values.yaml.j2) `postgres.replicaCount` → StatefulSet `spec.replicas` | Count includes the primary. API default is one pod; root chart default is two. API requires at least one pod. |
| Configure PostgreSQL version | NOT IMPLEMENTED | NOT VALIDATED | No API/UI version field | Docker build uses `postgres:16.6-bookworm`; Helm `postgres.imageName` can be manually overridden, but no version compatibility or upgrade workflow exists. Local image build passed; registry promotion and live upgrades remain unverified. |
| Configure storage size on creation | IMPLEMENTED | SMOKE VALIDATED | `Postgres.pgStorageCapacity` → `postgres.storageCapacity` → PVC template; `MinioSpec.storageCapacity` → MinIO PVC | Existing-volume expansion is not implemented. PostgreSQL and MinIO require at least 1 Gi; this is initial sizing, not a supported resize workflow. |
| Select storage class through product | NOT IMPLEMENTED | NOT VALIDATED | Charts expose `storageClass`; UI payload helper mentions it | `Project` has no `storageClass` field and ignores extra fields; Jinja templates do not propagate it. Helm-only configuration exists. |
| Configure CPU / memory | PARTIALLY IMPLEMENTED | STATICALLY VALIDATED | No API fields; both chart families expose per-container resources | Helm requests/limits are configurable; API resource controls remain Planned. |
| Configure PgCat | PARTIALLY IMPLEMENTED | SMOKE VALIDATED | `Project.enablePgCat`, `DB`, `User` → [`pgcat-values.yaml.j2`](../../application/app/templates/pgcat-values.yaml.j2) → Secret → watcher → TOML | External pgcat.yaml Secret owns pools and routing by default; development generation retains explicit Patroni identifiers and single-pod handling. No PostgreSQL database/user creation accompanies pool configuration. |
| Configure MinIO | PARTIALLY IMPLEMENTED | SMOKE VALIDATED | `MinioSpec`, `deploy()`, [`minio-values.yaml.j2`](../../application/app/templates/minio-values.yaml.j2), application MinIO chart | StatefulSet, Secret, Service, hook Job exist. Single local data volume per pod; no distributed MinIO configuration. Existing backup-user passwords are not rotated by the hook. |
| Configure external S3 destination | PARTIALLY IMPLEMENTED | NOT VALIDATED | `WalGS3` → Patroni Jinja values → `.walg.env` Secret | No connectivity, bucket, permission, or recoverability validation; omitted values can retain unrelated chart defaults. |
| Configure backup schedule | PARTIALLY IMPLEMENTED | STATICALLY VALIDATED | `WalGBackup.backupSchedule` → `backup.BACKUP_PERIOD` → CronJob | Numeric five-field cron is validated and quoted. Job requires one scoped primary and propagates WAL-G failure; Schedule syntax is statically checked; a manual Job from this CronJob produced a live verified MinIO backup. Scheduled firing itself is not tested. |
| Trigger backup now | NOT IMPLEMENTED | NOT VALIDATED | No backup endpoint or UI action | CronJob embeds `wal-g backup-push`; an operator can invoke tools manually. |
| List backups | NOT IMPLEMENTED | NOT VALIDATED | No product backup-list endpoint; recovery preflight calls WAL-G backup-list | No product backup catalog or age/status view. |
| Restore a backup | PARTIALLY IMPLEMENTED | LIVE VALIDATED | [`entrypoint.sh`](../../patroni/entrypoint.sh) `clone_with_walg`; restore script generated by both Patroni charts | Operator recovery selects a matching backup completed before target time; bootstrap honors BASE_BACKUP_NAME. No restore API. The opt-in runtime harness verifies recovered A/B/C data; recovery CLI completion alone still requires operator verification. |
| Perform PITR | PARTIALLY IMPLEMENTED | LIVE VALIDATED | [`ptr_recovery.sh`](../../scripts/ptr_recovery.sh), Patroni `recovery_target_time`, WAL-G `wal-fetch` | Experimental operator-only workflow: dry-run default, UTC timestamp, ownership/PVC checks, explicit execution. Provisioning rejects enablePITR. Target-time A/B/C recovery was exercised in the disposable lab; broader WAL gaps, timeline histories and off-site recovery remain untested. |
| Scale an existing cluster | PARTIALLY IMPLEMENTED | NOT VALIDATED | Resubmit same release to `deploy()` with new `pgReplicas`; Helm upgrades `spec.replicas` | No dedicated scaling API, role-aware scale-down, validation, progress state, or safeguards for deleting the current primary. Other values/releases are processed again. |
| Update existing deployment | PARTIALLY IMPLEMENTED | NOT VALIDATED | `helm upgrade --install` used for all three components | Some updates are immutable or not equivalent to DB operations; no atomic multi-release transaction, rollback, or operation locking. |
| Set superuser / replication credentials | PARTIALLY IMPLEMENTED | SMOKE VALIDATED | API `PostgresCreds`, Patroni Jinja template and environment | External Secrets are the default; optional inline UI fields require server development opt-in and map to generated values. Baseline correction: fields were absent, not dropped. No validated rotation of an initialized PostgreSQL cluster. |
| Manage application DB users / grants | NOT IMPLEMENTED | NOT VALIDATED | `User`, `AccessRule`, UI controls exist | Users feed PgCat authentication; no SQL `CREATE ROLE`, `CREATE DATABASE`, `GRANT`, or expiry implementation. Access rules remain accepted but unused; UI grant controls are disabled. |
| Rotate credentials | NOT IMPLEMENTED | NOT VALIDATED | No rotation endpoint or reconciled procedure | Changing Helm values/Secrets does not prove database and client passwords rotate consistently. MinIO existing-user branch skips password replacement. |
| Preview generated values | PARTIALLY IMPLEMENTED | STATICALLY VALIDATED | `POST /api/values/preview`, `preview()` | Shares deploy context, escapes HTML and redacts credentials/endpoints. No UI call to this endpoint was found. |
| Access monitoring from product | NOT IMPLEMENTED | NOT VALIDATED | Monitoring model / toggles exist | Controls are disabled and marked Planned; backend has no monitoring deployment step. Separate operator-managed manifests exist. |
| Authenticate users / authorize operations | PARTIALLY IMPLEMENTED | STATICALLY VALIDATED | Bearer authentication for /api/*; operator namespace allowlist | Shared operator identity; no user/session model or per-release ownership. Missing token configuration disables the API. |
| Tenant isolation | NOT IMPLEMENTED | NOT VALIDATED | Caller chooses release and namespace | Shared operator token and namespace allowlist exist; no per-user ownership, tenant RBAC, enforced tenant NetworkPolicies, quotas or tenant-specific limits. Chart selectors and pgAdmin names are now release-scoped; that does not provide tenant authorization or network isolation. |
| Reconcile desired state / repair drift | NOT IMPLEMENTED | NOT VALIDATED | Backend runs one sequence per request | Kubernetes controllers and Patroni reconcile their own resources; no application controller reconciles the overall service. |

## Fields that overstate current behavior

| Field / UI control | Actual effect |
|---|---|
| Database definitions | Development mode configures PgCat pools; external mode uses operator-managed pgcat.yaml. No database creation. |
| User definitions | Configure PgCat users; do not create corresponding PostgreSQL roles. |
| `databaseAccess`, `validUntil` | Accepted by API with no enforcement; grant control disabled and marked Planned. |
| `enablePITR` | Rejected by provisioning; Experimental operator recovery uses restore bootstrap explicitly. WAL archiving and CronJob creation remain unconditional. |
| Monitoring switches | Disabled and marked Planned; unused by deployment templates. |
| Superuser / replication form inputs | Development-only; external Secret references are submitted by default. Password defaults are empty. |
| `BASE_BACKUP_NAME` | Restore script honors it; operator recovery selects it from WAL-G metadata before executing. |

## Conclusion

**A PostgreSQL DBaaS prototype with an existing provisioning control plane** is an accurate description. A complete managed database lifecycle, secure multi-tenancy, production HA and production disaster recovery remain unproven. Lab backup/PITR and pod failure evidence has a narrower scope. See the [technical audit](technical-audit.md) and [risk register](runtime-risk-register.md) for supporting analysis and remediation order.

## Historical Phase 3 reliability boundary (superseded by Phase 4)

Resources, role-aware probes, configurable scheduling, conditional PDBs, manual StatefulSet updates, backup deadlines and recovery state journals are implemented in both chart families. Seven controlled image builds passed. Disposable kind creation, image loading and API startup passed; authenticated provisioning failed when Helm could not reach the in-cluster Kubernetes API (`EOF`). Full SQL/backup/PITR validation has not passed. See [Phase 3 evidence](phase3-reliability-report.md).

## Infrastructure validation

| Capability | Validation | Boundary |
|---|---|---|
| Seven pinned image recipes | BUILD VALIDATED | Local Docker builds; no signed registry promotion or multi-architecture proof. |
| API ServiceAccount → Kubernetes API | LIVE VALIDATED | Mounted token/CA, TLS verification, namespace RBAC and Helm; no cluster-admin. |
| Primary/replica replication and role Services | LIVE VALIDATED | Two members on one kind node; cannot establish node-level HA. |
| SQL through PgCat | LIVE VALIDATED | Independent client via Service; writes and primary/replica backend observations. |
| Operator backup and WAL archive | LIVE VALIDATED | CronJob-derived Job, WAL-G catalog and actual MinIO objects. No backup API. |
| Controlled primary and replica failures | LIVE VALIDATED | Pod deletion and acknowledged test-row verification; bounded sampled observations. |
| PgCat interruption | LIVE VALIDATED | Single proxy; reconnecting clients only. See final report for deletion versus earlier rolling restart. |
| Backup during writes | LIVE VALIDATED | Completed backup and writes; this additional backup was not separately restored. |
| NetworkPolicy enforcement / multi-node drain | NOT VALIDATED | Default kind CNI and one-node topology cannot establish these properties. |
| Resource limits, PDBs and topology controls | STATICALLY VALIDATED | Render checks; live drain and capacity behavior remain untested. |
| Monitoring/logging integration | NOT VALIDATED | No Prometheus/Grafana/Loki installation or fabricated metrics. |

## Phase 5 evidence update (2026-10-03)

The earlier audit remains historical. Current scope is in the [Phase 5 report](phase5-resilience-evidence-report.md) and [claim index](../evidence/README.md).

| Capability | Current classification | Boundary |
|---|---|---|
| Three-member, multi-worker provisioning/replication | LIVE VALIDATED | One physical host; local-path storage |
| Two PgCat replicas and affected-session recovery | LIVE VALIDATED | Explicit client reconnect/TCP timeout; no session migration |
| Graceful drains and PDB behavior | LIVE VALIDATED | Local PVC replacement waits for its node |
| Abrupt node-loss promotion | EXPERIMENTALLY MEASURED | Automatic replica convergence failed; manual reinitialization |
| Calico NetworkPolicy allow/deny | LIVE VALIDATED | Tested namespace/profile only |
| Isolated PITR and ordinary clone restart | LIVE VALIDATED | Earlier clone crash failed; corrected-clone abrupt loss remains incomplete |
| External S3 helper/harness | STATICALLY VALIDATED | Actual off-site recovery NOT VALIDATED |
| Application/PgCat rotation and configuration revision | LIVE VALIDATED | Other credential classes/major upgrades NOT VALIDATED |
| Metrics, five dashboards, one alert transition | LIVE VALIDATED | Partial exporter/log coverage; broken kind targets |
| 24-point pgbench and backup/restore samples | EXPERIMENTALLY MEASURED | Transaction pooling, short shared-host samples |

## Phase 5 continuation

| Capability | Classification | Boundary |
|---|---|---|
| Automatic rejoin in clean abrupt-loss reruns | LIVE VALIDATED | Historical stuck-replica attempt remains FAILED with unresolved trigger |
| Clone source-archive detachment and crash durability | LIVE VALIDATED | Graceful and abrupt pod replacement; one-member clone, no independent storage failure |
| Watcher bounded graceful shutdown | LIVE VALIDATED | Both containers exited zero; established proxy sessions can reset |
| Application credential reload with existing sessions | LIVE VALIDATED | Disposable role, two proxies; replication credential rotation NOT VALIDATED |
| Operator admission TLS | LIVE VALIDATED | CA-backed webhook, fail-closed rule validation; not end-to-end database TLS |
| Four availability/backup alert transitions | LIVE VALIDATED | Real workload faults; notification delivery NOT VALIDATED |
| Off-site backup and restore | NOT VALIDATED | No external target supplied |

See the [continuation report](phase5-continuation-report.md) for attempts, regression fixes and measured bounds.
