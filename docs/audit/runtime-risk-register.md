# Runtime risk register

> Phase 6 navigation: this document retains its historical audit scope. For current classifications and remaining risks, use the [authoritative evidence index](../evidence/README.md) and [production gap analysis](../report/production-gap-analysis.md).

Continuation results: [Phase 5 follow-up](phase5-continuation-report.md). Historical failed outcomes below remain preserved; see the follow-up for current validation scope.

> Phase 4 update (2026-10-03): the [runtime report](phase4-runtime-validation-report.md) supersedes the historical EOF blocker and untested backup/PITR statements below. Validation labels describe the exact evidence scope, not production readiness.

> Phase 3 update (2026-10-03): [reliability report](phase3-reliability-report.md) supersedes baseline findings about resource requests, probes, scheduling/PDBs, shutdown, backup deadlines and build validation. Both chart families now implement those controls; live provisioning remains blocked by the recorded in-cluster API connection failure. Earlier sections retain their dated audit evidence.

> Phase 2 update (2026-10-03): the [security and reproducibility report](phase2-security-reproducibility-report.md) supersedes earlier authentication, credential-default, preview/logging and dependency findings. Default chart/API input now uses external Secrets; inline values require development opt-in. Phase 1 behavior remains covered by regression tests. Earlier sections preserve their dated evidence.

Audit date: 2026-10-01. Source revision: `c275fc2dd3c4e8e9db1e28eadf50100e3cfcbbc1`. The table below preserves baseline findings; the Phase 1 status section supersedes changed findings and recommendations.

## Reading the register

**CONFIRMED** means the source or a local render/mock reproduces the defect, not that an outage was observed. **HIGHLY LIKELY** means the code path strongly predicts the consequence, subject to deployment conditions. **POSSIBLE** marks an unverified integration concern. Severity describes impact when the affected path is used. CRITICAL exposure findings are conditional on an untrusted caller reaching the deployed service. Recommendations are **Planned** work.

Paths beginning `helmCharts/` have matching affected application copies where stated. `main.py` means [`application/app/main.py`](../../application/app/main.py). No credential values are reproduced.

## Phase 1 status — 2026-10-01

These are source/local-test outcomes, not deployed outcomes. See [Phase 1 report](phase1-correctness-report.md) for changed files, commands, migration requirements, and remaining runtime checks. Original line numbers below refer to the audited revision.

| IDs | Current status |
|---|---|
| R02, R05 | Default chart RBAC is namespaced; API requires an operator-prepared namespace/binding. Backend Role covers child chart permissions. Optional API bypass retains namespace-correct cluster RBAC. Live authorization remains untested. |
| R03, R28 | Fixed: explicit Patroni release identifier, shared preview/deploy context, module-relative static/chart lookup and strict templates. |
| R04, R20 | Fixed: quoted schedules, scoped primary selection, fail on discovery/empty/multiple targets, stdin forwarding, primary verification and WAL-G exit propagation. Mock-validated; no real backup produced. |
| R06–R08 | Partially addressed: dry-run default, explicit execute, ownership/PVC/backup preflight, absolute chart paths and selected backup honored. Still destructive in-place recovery; WAL coverage and target data unverified. Isolated restore remains Planned. |
| R10 | Temporary-file collision/cleanup fixed using private directories and mode 0600 files. Per-release operation locking remains Planned. |
| R11, R12 | Single tested UI handler; optional admin/replication fields added and submitted. **Baseline R12 correction:** those input fields/mappings were absent; the earlier claim that collected credentials were dropped was inaccurate. |
| R13, R14 | Misleading UI controls corrected: database/user fields describe PgCat configuration; grants/monitoring disabled and Planned; provisioning rejects PITR. SQL provisioning remains NOT IMPLEMENTED. |
| R15, R16, R19 | Fixed in both active chart families: release selectors/names, standard PgCat defaults, named metrics endpoint backed by configured exporter port. Immutable-field migration required. |
| R17 | Partially addressed: preview HTML escaped, browser payload logging removed. Preview credentials and raw subprocess output remain exposed to authorized network callers; authentication/redaction deferred. |
| R18 | Input bounds/enums/names, YAML/TOML serialization and password quoting improved and tested. Direct Helm values and broader semantic validation remain operator responsibilities. |
| R21 | Initial configuration gated by init container; watcher validates, writes atomically and watches projected directory. Rebuilt watcher image required; actual Secret reload/PgCat behavior untested. |
| R24 | Matching Patroni governing Service added; MinIO serviceName matches chart Service. Live MinIO immutable-field migration required. |
| R25 | Chart pgAdmin replica host fixed; chart ingress opt-in with explicit hostname. Standalone legacy ingress remains unchanged. |
| R26, R27 | Ordered Helm waits, failure propagation, completed-release reporting and root CLI dependent names fixed; root MinIO initialization is now a hook. No transactional rollback, durable state or locking. |
| R30 | API single-pod topology emits primary-only PgCat backend and enables primary reads. Direct Helm users must configure topology consistently. |
| R01, R09, R22, R23, R29, R31–R33 | Unchanged: security/default credentials, raw-manifest defects, network/HA assumptions, Rook metadata, storage expansion and MinIO rotation require later work. |

## Baseline confirmed and probable defects

| ID | Severity | Confidence | Finding / impact | Affected source | Recommended fix |
|---|---|---|---|---|---|
| R01 | CRITICAL | CONFIRMED | Deployment API has no caller authentication, ownership checks, or namespace authorization. Reachable callers can request provisioning/upgrades using the backend's Kubernetes identity. Actual scope depends on granted RBAC; current restrictive/broken RBAC is not an application security boundary. | `main.py`: `deploy()`, `DeploySpec`; `application/k8s/ingress.yaml` | Require authenticated identity, enforce namespace/release ownership and operation authorization before allowing provisioning; retain least privilege. |
| R02 | HIGH | CONFIRMED | Backend Role lacks ServiceAccounts, Roles, RoleBindings, ClusterRoles/Bindings, namespace creation, and Traefik IngressRoutes required by selected charts. Supplied installation cannot independently provision the complete stack. | `application/k8s/rbac.yaml:12`; `main.py:321`; both Patroni charts; PgCat `pgadmin.yaml` | Define explicit bootstrap/admin vs provisioner responsibilities; preinstall restricted shared RBAC or redesign charts. Do not grant cluster-admin as a shortcut. Account for RBAC bind/escalation checks. |
| R03 | HIGH | CONFIRMED | PgCat Jinja receives no `_patroniRelease`; actual mocked `deploy()` renders `patronimvp-master-` and empty `patroniReleaseName`. Backend routing targets do not name the created Services. | `main.py:294`; `application/app/templates/pgcat-values.yaml.j2:2,35,37` | Pass one explicit Patroni release name, use it consistently in preview/deploy, fail on undefined Jinja variables, test generated service references. |
| R04 | HIGH | CONFIRMED | Backup selector renders `OnFailure,release-name=<release>`. This is a label-existence selector for `OnFailure`, not an invalid selector; chart pods lack that label. Job normally backs up nothing. Empty lookup and lookup failure both exit zero in a shell mock. | Both `helmCharts/patroni/templates/backup_cronjob_k8s.yaml:59–69` | Use `backup.LABEL_SELECTOR`, add release scope, fail on empty/error results, verify primary role and backup exit status. |
| R05 | HIGH | CONFIRMED | Root Patroni cluster binding authorizes `default:<release>-patronimvp`, while `deploy.sh` installs the pod in `dbaas`. The actual SA lacks the intended read on `default/kubernetes` Endpoints used by API bypass. | `helmCharts/patroni/templates/patroni_k8s.yaml:299–305`; `scripts/deploy.sh:47` | Match release namespace and namespace-aware RBAC naming, or remove bypass and its extra privilege after testing. Exact startup impact depends on Patroni version/fallback. |
| R06 | CRITICAL | CONFIRMED | Recovery uninstalls PgCat and Patroni and attempts PVC deletion before verifying backup availability or chart paths. Can remove the only recoverable local data; error suppression can hide failed cleanup. | `scripts/ptr_recovery.sh:50–65,87–95` | Restore into a new isolated release/PVC set, validate backups first, verify target data, explicitly control cutover and cleanup. Never make in-place deletion the default. |
| R07 | HIGH | CONFIRMED | Recovery fixes namespace to `default` while script deployment uses `dbaas`; Patroni chart path works from `scripts/`, PgCat path from repository root. It can stop/delete resources and then fail to reinstall. | `scripts/ptr_recovery.sh:44–47`; `scripts/deploy.sh:37–47` | Resolve paths from script location, require explicit namespace/context/release inputs, run preflight before mutations. |
| R08 | HIGH | CONFIRMED | Restore always fetches `LATEST`, ignoring `BASE_BACKUP_NAME`. A base backup newer than target time cannot support the intended earlier PITR; script success only checks rollout, not recovered data/time. | Both Patroni templates, init restore script; `patroni/entrypoint.sh:27–33`; recovery script | Select a suitable backup by target, validate timeline/WAL coverage, verify recovery result before exposing writes. |
| R09 | HIGH | CONFIRMED | Credentials/defaults are tracked and can become live credentials. Root MinIO and raw PgCat expose credentials in ConfigMaps. Publicly available defaults are unsafe for live deployments. | Chart values in both trees; `kuberResources/{minio_k8s,patroni_k8s,patroni_backup_k8s,proxy}.yaml`; watcher default config; PgCat Jinja fallback | Use supplied Secret references and no usable committed credentials. Classify/rotate any previously deployed values; removing a value from the current tree does not remove Git history. |
| R10 | HIGH | CONFIRMED | `_debug_write_yaml()` uses predictable release/component/second paths, includes no namespace, opens with `w`, relies on umask, never cleans up, and follows existing paths. Requests may overwrite each other's credential-bearing values. Unvalidated release strings influence paths. | `main.py:265–275,318,345,369` | Private temporary directory/file with exclusive creation and 0600, cleanup in `finally`, safe names, operation IDs, per-release locking. Arbitrary file overwrite exploitability is not demonstrated. |
| R11 | HIGH | CONFIRMED | UI script 1 throws `ReferenceError: cfg is not defined` at top level, preventing its later listener/init calls. Script 2 still registers `handleSubmit`. Removing the exception alone would activate both handlers and could double-submit. | `application/static/index.html:685–744,747–843` | Consolidate to one initialization and submission path; test one HTTP operation per submit with/without MinIO. |
| R12 | HIGH | CONFIRMED | UI collects superuser/replication credentials but both submit payloads omit them. Operator-entered credentials are not the ones used to provision PostgreSQL. | `index.html`: `buildNestedConfig()`, both PostgreSQL payload objects; `main.py:50–55` | Propagate validated credentials or Secret references; test payload-to-render parity. |
| R13 | HIGH | CONFIRMED | Form fields imply database/user/grant management, but backend creates none of those SQL objects. PgCat may authenticate a configured user that does not exist in PostgreSQL. | `main.py`: `DB`, `User`, `AccessRule`, `deploy()`; PgCat Jinja; UI | Clearly mark controls Experimental or implement validated, authorized SQL provisioning and grants before claiming support. |
| R14 | HIGH | CONFIRMED | `enablePITR` maps directly to restore bootstrap, without target timestamp or backup selection. Enabling what looks like backup capability on a fresh service can instead attempt restore from an empty/unrelated bucket. | UI PITR control; `patroni-values.yaml.j2:13`; `entrypoint.sh:10–15` | Separate backup/archival enablement from an explicit restore operation with target validation. |
| R15 | HIGH | CONFIRMED | PgCat and pgAdmin Services select all matching `app` pods in a namespace; pgAdmin Secret/ConfigMap names are fixed. Multiple releases collide or route across services. Root MinIO Service has the same selector issue; app MinIO fixes Service selection but not broad StatefulSet selector. | Both PgCat `proxy.yaml`, `pgadmin.yaml`; both MinIO templates | Scope selectors/resources by release with an immutable-field migration plan. Test two independent releases in one namespace. |
| R16 | MEDIUM | CONFIRMED | PgCat metrics Service targets 9898; watcher/Jinja/defaults configure 9930. Scraping the Service does not reach the configured exporter. | `serviceMonitor/pgcat-service.yaml`; watcher `generatePgcatConfig()`; PgCat values | Use the configured exporter port consistently, preferably from a chart value shared by ServiceMonitor and container. |
| R17 | HIGH | CONFIRMED | Preview returns rendered values including passwords, unescaped inside HTML; UI logs full submit payload. Credential redaction in Python context logging does not protect these outputs. | `main.py:252–263`; `index.html:794`; Jinja templates | Redact preview by default, return structured/escaped content, remove sensitive browser logging; avoid raw Helm error/output disclosure. |
| R18 | HIGH | CONFIRMED | User strings are interpolated into YAML/TOML without appropriate serialization. A synthetic quoted username causes YAML parse failure; crafted values could alter configuration. SQL/access enums and numeric bounds are weak; DNS validator exists but is never called. | `main.py:39–134`; Patroni/PgCat Jinja; watcher interpolation; Patroni entrypoint | Validate identifiers/ranges/enums; serialize configuration data rather than concatenate; use strict templates and safe file naming. Subprocess argument lists already avoid a shell in the backend. |
| R19 | MEDIUM | CONFIRMED | Application PgCat has `pgcat-values.yaml`, not `values.yaml`; plain Helm lint/template fails on missing `pgcatconfig.general`. Generated application values omit a default pool when database list is empty. | `application/helmCharts/pgcat/`; PgCat Jinja `DBS` loop | Supply documented defaults/schema and require at least one valid pool or deliberately disable PgCat. Explicit `-f pgcat-values.yaml` currently renders successfully. |
| R20 | MEDIUM | CONFIRMED | Cron schedule is inserted without quoting. Rendering an otherwise valid leading-star schedule such as every five minutes fails YAML parsing. | Both Patroni `backup_cronjob_k8s.yaml:42` | Quote schedule in chart; validate cron server-side and test common expressions. |
| R21 | HIGH | HIGHLY LIKELY | PgCat starts concurrently with watcher against empty shared directory. No startup gate/probes; watcher catches errors and remains alive, writes non-atomically, and only handles `change` events. Config can be absent, partial, stale, or missed on projected Secret replacement. | Both PgCat `proxy.yaml`; watcher `ensureConfigExists()`, `applyConfig()`, `watchConfig()` | Generate initial config before PgCat starts, validate TOML, atomic rename, handle projection updates, propagate health/failure. Reproduce with actual chosen PgCat/chokidar versions. |
| R22 | HIGH | CONFIRMED | Raw DB Services use `spec.matchExpressions` with null `spec.selector`, not Service selector maps. They do not implement intended role-based pod selection. | `kuberResources/db_services_k8s.yaml` | Use supported Service label maps and appropriate positive pod labels; schema validation. Strict admission may reject unknown fields; permissive handling still leaves no selector. |
| R23 | HIGH | CONFIRMED | Raw Patroni init containers copy `/commands`, but WAL-G Dockerfile never creates/copies it. Raw recovery SA binding also names the non-backup SA. | `kuberResources/patroni_k8s.yaml`, `patroni_backup_k8s.yaml`; `wal-g/Dockerfile` | Bring raw path in line with maintained restore script packaging; correct binding; test from locally built images. Existing published image contents are unknown. |
| R24 | MEDIUM | CONFIRMED | StatefulSet governing Service names do not match defined headless Services: MinIO uses `minio` but creates `<release>-minio`; Patroni uses `<release>-patronimvp` but only explicitly creates `<release>-patronimvp-config` plus role Services. | Both MinIO/Patroni StatefulSet templates | Provide matching governing Services; avoid renaming live StatefulSets/PVCs without migration. Pod-IP connections may work despite missing stable per-pod DNS. |
| R25 | MEDIUM | CONFIRMED | Both pgAdmin server entries for master/replica point to the master Service. Standalone pgAdmin ingress references `pgadmin-service`, not chart Service name. | Both PgCat `pgadmin.yaml`; `ingress/pgadmin.yaml` | Correct replica endpoint; parameterize ingress backend/release names. |
| R26 | HIGH | CONFIRMED | No application rollback or transactional recovery across three releases. Helm calls lack `--atomic`; sleeps substitute for checks; exceptions leave earlier components running. No application concurrency control. | `main.py`: `run()`, `deploy()` | Durable operation status, time-bounded execution, per-release lock, retry/compensation policy; preserve data on failures. Helm locks alone do not protect shared temp files or all three releases. |
| R27 | MEDIUM | CONFIRMED | `deploy.sh` does not fail fast on every Helm error and can report final success after PgCat failure; custom release flags do not propagate dependent backend/MinIO names. Root MinIO normal Job can block upgrades via immutable pod-template changes. | `scripts/deploy.sh`; root chart values; root MinIO Job | Check every command, resolve chart paths, propagate release-dependent values, use upgrade-safe initialization semantics. |
| R28 | MEDIUM | CONFIRMED | Preview context lacks top-level `release`; MinIO endpoint rendered by Patroni preview differs from deploy. Chart selection can change with working directory. | `main.py`: `preview()`, `deploy()`, `find_chart()` | Share context generation and explicit chart source; require preview/deploy parity. |
| R29 | HIGH | HIGHLY LIKELY | Replication HBA assumes pod IP plus `/16`; arbitrary CNI ranges may not fit. No TLS requirement, no synchronous replication policy, no node spreading; availability/durability can fall short of implied HA. | `patroni/entrypoint.sh:19–39`; both Patroni templates | Explicit network/auth policy and tested replication/failover settings; choose synchronous policy by durability/availability requirements. |
| R30 | HIGH | CONFIRMED | API single-pod default means PgCat's replica Service has no backend; configured primary reads default false. Multi-pod chart defaults do not prevent this API configuration. | `Postgres.pgReplicas`; PgCat Jinja/defaults; primary/replica Services | Validate topology against routing policy; define deliberate read behavior for single-pod clusters and failover. Exact PgCat fallback requires runtime test. |
| R31 | MEDIUM | CONFIRMED | Rook gitlink has no `.gitmodules` entry. Reproducible submodule initialization fails. | `rook-config/rook` index entry | Restore proper pinned submodule metadata or explicitly document external Rook installation; do not imply a deployable Ceph backend. |
| R32 | HIGH | HIGHLY LIKELY | Changing PVC template size through generic Helm redeploy is not a supported live expansion procedure and can fail on immutable StatefulSet fields. | Patroni/MinIO Jinja and volumeClaimTemplates | Distinguish initial size from expansion, inspect CSI capabilities, implement PVC expansion without destructive replacement. |
| R33 | MEDIUM | CONFIRMED | MinIO app hook does not update an existing backup user's password but generated WAL-G Secret follows new input. A password change can break archival after a successful hook. | App MinIO `init-minio.sh`; Patroni values generation | Implement coordinated credential rotation with verification, or reject unsupported rotation explicitly. |

## Important corrections and unverified concerns

### Recovery PVC selector is not a confirmed no-op

The chart's PVC template lists `application: spilo` and `spilo-cluster: patronimvp`, whereas the recovery command selects `application=patroni,release-name=<release>`. Comparing these two snippets alone suggests a mismatch. However, Kubernetes' StatefulSet controller merges the StatefulSet selector labels into newly generated claims and overwrites matching keys. For these charts, newly created claims can therefore carry the labels targeted by deletion. The live label set and cluster version were not inspected. Treat deletion as genuinely destructive, not safely ineffective. Existing/imported/raw-manifest claims may differ. [Kubernetes controller source, `getPersistentVolumeClaims`](https://github.com/kubernetes/kubernetes/blob/master/pkg/controller/statefulset/stateful_set_utils.go).

### Other integration risks

- **POSSIBLE:** published custom Patroni/WAL-G images differ from these Dockerfiles; no provenance or digest confirms equivalence. PostgreSQL/Patroni role-label compatibility must be tested for the image actually deployed.
- **POSSIBLE:** MinIO `/minio/metrics/v3` scrape path and Fluent Bit/Loki values may not match selected external versions. No corresponding chart versions or live targets are recorded.
- **POSSIBLE:** hardcoded `fsGroup: 999` differs from the actual image's PostgreSQL UID/GID; verify image and filesystem permissions before asserting a defect.
- **POSSIBLE:** WAL-G standalone image command composition and Ubuntu-built binary compatibility with the final PostgreSQL image need a container smoke test. Normal Helm init containers override the standalone command.
- **POSSIBLE:** TLS certificate provisioning and ingress connectivity depend on externally installed controllers/issuers; referenced CRDs are not installed by repository scripts.
- **CONFIRMED configuration risk:** no backup retention, object-lock, off-cluster copy, or backup verification policy is configured. This is a missing operational guarantee, not proof that every deployment loses data.
- **CONFIRMED configuration risk:** no container CPU/memory budgets, PDB, node spreading, or application-level tenant limits are supplied for the database stack. These require topology-aware implementation, not indiscriminate additions.

## Baseline highest-risk groups

1. R01/R09/R17: unauthenticated provisioning and unsafe credential handling if deployed beyond a trusted lab.
2. R04: backup jobs can succeed without creating any backup.
3. R06–R08: destructive restore path without preflight or verified recovery outcome.
4. R02/R05: supplied Kubernetes permissions and namespaces block intended provisioning/coordination.
5. R03/R15: broken PgCat service names and insufficient release isolation affect connection correctness.

## Baseline local evidence collected

- Rendered both Patroni charts; inspected exact CronJob selector and root ClusterRoleBinding subject.
- Ran CronJob shell body with mock `kubectl` returning either empty success or failure; both produced exit status zero. No real kubectl executed.
- Called real `deploy()` with synthetic request data while replacing subprocess runner, file writer, and sleeps; confirmed truncated PgCat hostname and response keys.
- Rendered synthetic quoted username; YAML parser rejected generated configuration.
- Rendered leading-star cron override; Helm reported a YAML parse error.
- Executed the two UI script blocks in a Node VM with a stub DOM; confirmed first-block `cfg` ReferenceError and later registration of `DOMContentLoaded`. This is not a browser integration test.
- Tested real Pydantic request models; negative replica count and traversal-like release name were accepted. No filesystem write or deployment was attempted with those inputs.
- Rendered preview using synthetic credentials; response included the synthetic password.
- Inspected current tracked credential fields without copying values into audit documents. No exhaustive Git-history secret scan or credential validity test was performed.

## Phase 4 runtime status — 2026-10-03

| Risk / capability | Validation | Current evidence and residual risk |
|---|---|---|
| API Kubernetes EOF / R02, R05 | LIVE VALIDATED | Root-host inotify instance exhaustion prevented kube-proxy startup; temporary lab host adjustment restored CA-verified in-pod HTTPS and Helm. Required namespaced permissions passed. No broader RBAC added. |
| Provisioning / R03, R19, R24–R27 | SMOKE VALIDATED | Real authenticated API created MinIO, two-member Patroni and PgCat. Fixed OnDelete readiness waits, MinIO init retries and invalid pgAdmin email default. No durable operation lock or transactional rollback. |
| Backup / R04, R20 | LIVE VALIDATED | Authenticated loopback TCP fixes the primary check; CronJob-derived Job produced catalog entries and actual backup/WAL objects. Schedule execution, retention and off-site protection untested. |
| Recovery / R06–R08 | LIVE VALIDATED | A exists, B after target absent, C writable/replicated in the lab. Fixed role-Service Endpoint inventory and shutdown-before-uninstall race. Destructive in-place recovery remains opt-in; isolated restore/cutover Planned. |
| PgCat / R15, R21 | LIVE VALIDATED | Initial configuration, Service routing and SQL verified. Secret reload and multi-release isolation under live traffic remain NOT VALIDATED. |
| Pod failure recovery | LIVE VALIDATED | Primary/replica and proxy tests record client samples. Acknowledged synthetic IDs checked; asynchronous replication is not a zero-loss guarantee. |
| Local image supply / dependencies | BUILD VALIDATED | Seven local image builds. Signing, SBOM verification, registry promotion and cross-architecture builds Planned. |
| Probes/resources/PDBs/topology | STATICALLY VALIDATED | Render/unit checks and ordinary startup passed. Multi-node drain, resource exhaustion, storage detachment and real failure domains NOT VALIDATED. |
| Network isolation | NOT VALIDATED | Default kind CNI does not enforce policy. Optional policies remain disabled; no claim of tenant isolation. |
| Credentials / R01, R09, R17 | STATICALLY VALIDATED | Authentication/redaction and secret scans pass; successful live API authentication also exercised. Shared operator identity, TLS to clients/storage and credential rotation remain gaps. Invalid upstream WAL-G config can echo sensitive content to pod logs; operators must restrict logs. |
| Monitoring, upgrades, scale-down, cloud storage, multi-tenancy | NOT VALIDATED | No production evidence added for these operations. |

Remaining SPOFs: one physical lab node, one MinIO instance/local volume, one PgCat replica and one API replica. Database replicas share a failure domain. A local object-store backup cannot survive loss of that shared storage/node. PostgreSQL replica count alone does not establish platform HA.

All historical findings above retain their original dates; use the Phase 4 report and per-attempt JSON for current outcomes. Failed runs are retained under `results/runtime/attempts` and never merged into a new run's PASS status.

## Phase 5 findings (2026-10-03)

| Risk | Observed result / mitigation | Remaining boundary |
|---|---|---|
| Replica remains in archive recovery after node loss | Historical failure required reinitialize; two clean reruns converged automatically with diagnostic evidence | Historical FAILED remains open; exact trigger unresolved |
| Restored clone reads divergent source archive | New archive-read flag and live post-bootstrap check; fresh clone passed pod restart | Graceful and abrupt clone pod replacement LIVE VALIDATED; independent worker/storage loss NOT VALIDATED |
| Session pooling binds read-first mixed workloads to a replica | Aborted pgbench output retained; final benchmark uses transaction mode | Historical session default unchanged; choose workload-compatible mode |
| Persistent client TCP send stalls | Final probe adds tcp_user_timeout=5000 | Client-specific recovery, not transparent proxy failover |
| Graceful proxy replacements exceed harness bound | Watcher stayed alive until grace expired; 1.1.1 handles signals and exits promptly | Retain 90-second grace for PgCat client drain; sessions can disconnect |
| Monitoring partial/misconfigured targets | Actual inventory, dashboard queries and alert transitions captured | SQL/API/logging gaps and refused kind targets remain |
| Shared-host/local storage disaster recovery | Isolated restoration and external configuration helpers | Independent off-site recovery NOT VALIDATED |

[Phase 5 evidence and limitations](phase5-resilience-evidence-report.md). Original Phase 4 observations above are not replaced by broader production claims.
