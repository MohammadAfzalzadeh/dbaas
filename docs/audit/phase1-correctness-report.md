# Phase 1 correctness report

> Phase 2 update (2026-10-03): the [security and reproducibility report](phase2-security-reproducibility-report.md) supersedes earlier authentication, credential-default, preview/logging and dependency findings. Default chart/API input now uses external Secrets; inline values require development opt-in. Phase 1 behavior remains covered by regression tests. Earlier sections preserve their dated evidence.

## Implementation plan

| Confirmed bug / root cause | Affected files | Fix and expected behavior | Regression risk | Validation |
|---|---|---|---|---|
| Unset Patroni identifier, different preview context, leaking temporary files, weak input validation | FastAPI and Jinja templates | Shared validated context; deterministic names; scoped temporary directory; propagate partial failure | Invalid formerly accepted requests rejected | Mock API calls and render-to-Service assertions |
| Backup selector uses restart policy and shell ignores failures | Both Patroni CronJobs | Select exactly one primary of this release; fail empty/multiple/error; propagate WAL-G failure | Previously green no-op Jobs now fail | Execute rendered shell against fake kubectl |
| Shared selectors, missing PgCat defaults/ports, wrong namespace binding | Both chart families and ServiceMonitors | Release-scoped selectors; chart defaults; named metrics port; namespace-aware RBAC | Immutable selector migration needed for existing controllers | Two releases in two namespaces, lint/render and selector checks |
| Provisioner cannot create chart RBAC | Backend RBAC and Patroni charts | Namespaced permissions matching child roles; ordinary API service by default; optional explicit bypass | Existing bypass users must choose compatibility value | Rendered resource/RBAC checks; live authorization remains required |
| Destructive recovery before validation, mismatched paths, no backup selection | Recovery tooling and restore bootstrap | Dry-run default; explicit execute; verify ownership, namespace, backup metadata and PVC set; preserve values | Old automation must opt into deletion; fail closed when evidence unavailable | Fake command runners; timestamp/ambiguous PVC/dry-run tests |
| UI throws before initialization; credentials lack a form/payload path | Browser UI | One handler, complete payload, no premature success, clear unsupported restore behavior | Unsupported fields must be clearly identified | Stub DOM/fetch tests and JS syntax |

No cluster changes, authentication, image pinning, chart-family consolidation, or transactional rollback are part of this phase.

## Correctness Issues Fixed

Scope: both active chart families remain separate. No live Kubernetes commands, image builds, commits or pushes were performed. Baseline revision: `c275fc2dd3c4e8e9db1e28eadf50100e3cfcbbc1`; results describe the uncommitted working tree on 2026-10-01.

### FastAPI provisioning and generated values

- **Problem/root cause:** unset `_patroniRelease`, different preview context, permissive inputs, predictable persistent temporary files, and sleep-based orchestration.
- **Files:** `application/app/main.py`, `application/app/templates/{patroni,pgcat}-values.yaml.j2`.
- **Fix:** shared strict context, deterministic `<project>-patroni` identifier and matching primary/replica Service hosts; serialized strings; DNS-safe release/namespace bounds; positive pod/storage counts; validated numeric cron and pool modes. Empty pool/user lists resolve to postgres and the selected chart's administrator credentials. Single-pod API requests emit a primary-only backend with primary reads enabled. WAL-G connects to postgres, rather than an uncreated requested database.
- **Fix:** per-request private temporary directory, files mode 0600, cleanup on success/failure; lint every selected chart before mutation; sequential Helm waits and subprocess failure propagation. Static/chart lookup works from repository root. Preview shares deploy values and escapes HTML. Chart defaults control PgCat image selection.
- **Validation:** MOCK-VALIDATED command sequence, names, namespace, file mode/cleanup, partial failure and input rejection. Generated YAML and PgCat TOML are parsed. Preview/deploy parity is checked. Route functions are invoked directly; HTTP transport/browser integration is not covered.
- **Rollback semantics:** no automatic rollback. A later Helm failure returns an API error with completedReleases; earlier releases and any partial failed release remain for inspection. Successful response means the Helm commands returned successfully, not verified SQL/routing/backup behavior. No durable operation status or per-release lock was added.

### Backup execution

- **Problem/root cause:** RESTART_POLICY was used as a selector; empty discovery and command failures could exit zero. A leading-star cron expression was unquoted. The exec path also needed stdin forwarding to deliver the embedded script.
- **Files:** both `patroni/templates/backup_cronjob_k8s.yaml` copies.
- **Fix:** require backup.LABEL_SELECTOR and append application, primary role, cluster and release scope. Use downward namespace, fail discovery errors/zero/multiple targets, print selected target, and invoke `kubectl exec -i ... -- bash -s`. Strict inner shell verifies `pg_is_in_recovery() = f`, then execs WAL-G backup-push. Nonzero psql/exec/WAL-G fails the Job. Schedule is quoted.
- **Validation:** MOCK-VALIDATED rendered scripts with fake kubectl/psql/WAL-G: missing selector, no target, discovery error, multiple targets, replica target and WAL-G failure all fail. Success requires reaching a successful fake backup command. No backup object was created or checked in MinIO.

### Helm, namespaces and isolation

- **Problem/root cause:** default namespace in root cluster binding, backend permissions missing child chart resources, broad selectors, pgAdmin fixed resource names, missing governing Services and nonstandard application PgCat defaults.
- **Files:** both families' Patroni, MinIO and PgCat templates/values; `application/k8s/rbac.yaml`; `scripts/deploy.sh`.
- **Fix:** RoleBinding subjects follow release namespace. Patroni uses the ordinary Kubernetes API Service by default; `kubernetes.bypassApiService=true` explicitly opts into namespace-correct cluster RBAC. The backend's namespaced Role holds permissions needed to create its child Roles/Bindings; no cluster-admin/bind/escalate shortcut was introduced. API namespaces and bindings must be prepared by an operator.
- **Fix:** release-specific PgCat/pgAdmin/MinIO selectors and pgAdmin names; matching selectorless Patroni governing Service and corrected MinIO serviceName. Patroni owns the same-name leader Endpoints; a Kubernetes Service selector would introduce a competing writer. The [Patroni Kubernetes documentation](https://patroni.readthedocs.io/en/latest/kubernetes.html) describes this Endpoints ownership. Per-pod DNS availability remains unverified; PostgreSQL routing uses the separate role Services. pgAdmin replica entry targets the replica Service. Chart pgAdmin ingress requires explicit opt-in and hostname. Application PgCat now has values.yaml while retaining pgcat-values.yaml compatibility.
- **Fix:** root CLI anchors chart paths, supports namespace, propagates custom MinIO/Patroni release names, waits and fails fast. Root MinIO initialization is a post-install/post-upgrade hook and no longer suppresses user/policy command errors. Existing rootPasword spelling remains supported.
- **Validation:** STATICALLY VALIDATED six chart lint runs; both families rendered as alpha/beta in dbaas/test-dbaas. Service/controller selectors cannot match the other release's rendered pods. Default charts emit no cluster RBAC; opt-in bypass subject namespace and child-role permission coverage are checked. Live admission and RBAC authorization remain untested.

### PgCat generation and metrics

- **Problem/root cause:** unresolved backend names; metrics Service targeted 9898 while config used 9930; concurrent startup against empty config; unsafe TOML interpolation and non-atomic updates.
- **Files:** `pgcat/pgcat-config-watcher.js`, both PgCat proxy templates/defaults, PgCat Jinja, `serviceMonitor/{pgcat,patroni}-service.yaml`, both Patroni DB Service templates.
- **Fix:** Helm derives absent hosts from explicit patroniReleaseName. Watcher validates configuration and quotes TOML identifiers/strings; no fallback credential config is created. Init container runs `--once` before PgCat starts. Updates use an atomic rename and watch the projected directory; invalid updates retain the last valid file.
- **Fix:** pgcatconfig.general.PROMETHEUS_EXPORTER_PORT is authoritative (default 9930). PgCat container and release Service share its value via named metrics port. ServiceMonitor selects chart Services and references that port. Patroni monitor similarly discovers role Services and their patroni port; broad standalone metrics Services are removed from source.
- **Validation:** STATICALLY VALIDATED actual Helm Secret → Node generator → Python TOML parser; backend names match rendered primary/replica Services. Custom exporter port, monitor selector/port and ingress host tested. MOCK-VALIDATED malformed/quoted generator input. Actual init startup, projected Secret events, PgCat reload and exporter responses require live tests.

### Recovery prerequisites and restore bootstrap

- **Problem/root cause:** uninstall/deletion occurred before backup checks; namespace/chart paths disagreed; restore ignored BASE_BACKUP_NAME and selected LATEST regardless of target; heredoc expanded runtime variables in the init container.
- **Files:** `scripts/ptr_recovery.sh`, new `scripts/recovery.py`, both Patroni templates, `patroni/entrypoint.sh`.
- **Fix:** wrapper retains release/time flags; Python preflight validates UTC timestamp, namespace, deployed releases, Helm ownership, StatefulSet/Service selectors, PgCat backend references, WAL-G configuration and saved-value consistency. It verifies PVC namespace/labels/name/Bound state, pod owner UID and claim mounts, and requires one ready primary for backup metadata inspection. Ambiguous/empty PVC selection fails. It identifies a matching cluster-host backup completed before target, or validates --backup-name.
- **Fix:** render both restore releases before any mutation. Print namespace, releases/cluster, target, selected backup and exact PVC names/UIDs. Default is dry-run; only --execute uninstalls. Preserve saved Helm values, recheck each claim identity before shutdown and deletion, delete only named reviewed claims, clean only recognized DCS names, and stop on command failure. Quoted restore heredoc defers expansion; bootstrap honors selected backup. Patroni password YAML escapes apostrophes.
- **Validation:** MOCK-VALIDATED invalid dates, empty/foreign PVCs, backup matching/time selection, dry-run without mutations, uninstall failure before deletion, and successful command sequence deleting only the reviewed claim and retaining settings. Embedded restore shell parses. No real PVC was touched.
- **Evidence limit:** metadata selection uses WAL-G detailed fields backup_name, hostname and finish_time; see [v3.0.7 backup detail implementation](https://raw.githubusercontent.com/wal-g/wal-g/v3.0.7/internal/databases/postgres/backup_detail.go). This is a conservative prerequisite, not proof of WAL continuity or successful PITR.

### Browser contract

- **Problem/root cause:** top-level undefined cfg stopped initialization; duplicate scripts would double-submit once that error was removed. Administrator/replication form fields were absent (correcting the original audit's claim that collected values were dropped).
- **Files:** `application/static/index.html`.
- **Fix:** one initialization/submit path, pending-request guard, await fetch, require successful HTTP status and `ok: true`, show structured failures. Optional complete credential pairs are submitted; missing pairs use defaults. Pod count explicitly includes primary. Unsupported statement mode removed. PgCat-only database/user semantics are explained; grant and monitoring controls are disabled/Planned. PITR directs operators to the Experimental script; API rejects provisioning PITR requests. Browser credential payload logging removed.
- **Validation:** four Node tests cover initialization, payload mapping, HTTP/response failures, pending/double submit and generator serialization. No product recovery endpoint exists; provisioning no longer falsely presents restore bootstrap as an end-to-end recovery action.

## Validation results

### STATICALLY VALIDATED

- `helm lint helmCharts/{minio,patroni,pgcat}` and `helm lint application/helmCharts/{minio,patroni,pgcat}`: all six charts pass (run once per directory).
- `helm template alpha <chart> --namespace dbaas` and test-dbaas, repeated for beta: six charts × two namespaces × two releases parsed/checked by tests. Additional renders exercise generated API values, bypass, cron, metrics and ingress overrides.
- YAML safe-load: 38 non-template YAML files, plus Helm-rendered manifests and nested PgCat configuration in tests.
- `bash -n` on four repository shell files; `sh -n` on both rendered restore init scripts.
- Python AST parsing: four files. `node --check`: two repository JavaScript files plus extracted inline UI script. JSON parsing: pgcat/package.json.
- `git diff --check`: passes.
- Runtime search: no old 9898 or _patroniRelease remains in maintained paths. RESTART_POLICY remains only as a legitimate restart policy/default, never as the backup selector. Hardcoded namespace: default remains in the two legacy raw Patroni manifests, outside the maintained chart path. No rendered chart resource is hardcoded to default.
- ShellCheck, yamllint and kubeconform are unavailable. YAML parsing is not Kubernetes schema/admission validation.

### MOCK-VALIDATED

```bash
PYTHONDONTWRITEBYTECODE=1 application/.venv/bin/python -m unittest discover -s tests -v
node tests/test_ui.js
```

Results: **19 Python tests pass; 4 Node tests pass**. Helm and Node must be installed; Python test runtime needs the existing application dependencies, PyYAML and Python 3.11+ for tomllib. No network dependency installation was performed. Mock recovery output may say EXECUTING, but its runner is replaced: all mutation commands are recorded without execution.

## Compatibility and operator requirements

1. **Rebuild images before using changed source.** The watcher init container requires the updated `--once` implementation; an older published watcher can hang init. Build this repository's pgcat image and set pgcatConfigWatcherImageName in the selected chart defaults or Helm values. Rebuild Patroni for entrypoint quoting changes; rebuild the backend to package updated API/UI/charts. Published image tags are unchanged and were not inspected, built or pushed. API-generated values now inherit PgCat images from the selected chart.
2. **Existing immutable controllers need migration.** PgCat/pgAdmin Deployment selectors and MinIO StatefulSet selector/serviceName changed. A direct Helm upgrade of old controllers may be rejected. Plan a maintenance window, verified backups, captured values/claim identities and a reviewed controller recreation that preserves PVCs. Do not use automatic force replacement or recovery's destructive mode as a migration shortcut. Patroni StatefulSet/PVC names and selector remain stable; its governing Service is added.
3. **pgAdmin compatibility:** Secret/ConfigMap names now include release; chart ingress defaults off. Explicitly set pgadminIngress.enabled and a unique pgadminIngress.host when needed. Standalone legacy ingress examples are unchanged and need manual name updates. Migrating previous root MinIO initialization to a hook also needs live upgrade validation.
4. **Namespace/RBAC:** prepare namespace and backend RoleBinding for every allowed namespace; the checked-in backend installation covers dbaas. API does not create namespaces. Operator CLI deploy retains create-namespace. API bypass is opt-in and requires operator-managed cluster permissions. ServiceMonitor namespace selection remains dbaas and must be adjusted for other namespaces.
5. **Monitoring migration:** applying modified monitor files does not delete the old standalone metrics Services already in a cluster. Inventory and remove those obsolete Services separately once their replacements are verified; no live cleanup was attempted.
6. **Recovery dependencies:** Python 3, PyYAML, Helm and kubectl; current context selects the cluster. Both Patroni and PgCat releases must exist and be deployed. A ready primary and matching detailed WAL-G hostname/completion metadata are required. Offline disaster recovery and PgCat-disabled recovery are not supported by this flow.

Example inspection (reads Kubernetes/WAL-G metadata; does not mutate cluster resources):

```bash
bash scripts/ptr_recovery.sh --namespace test-dbaas \
  --patroni-releasename example-patroni --pgcat-releasename example-pgcat \
  --recovery-time '2025-01-01 12:00:00'
```

Use a real, reviewed UTC target and installed release names. `--backup-name` can select an eligible backup explicitly. Adding `--execute` authorizes in-place uninstall and deletion of the printed PostgreSQL PVCs. Errors stop the sequence; there is no automatic rollback after deletion. Default dry-run is an intentional compatibility change for old automation.

## Remaining Correctness Risks

- In-place recovery remains **Experimental and destructive**. Metadata does not prove complete WAL, compatible timelines, readable full backup objects or correct recovery outcome. Kubernetes reads/deletes are not an atomic transaction; operator exclusivity is required. After a mid-sequence failure, manual recovery can be necessary.
- Source changes do not establish compatibility of published images, WAL-G binary, Patroni role labels, PgCat TOML semantics/reload or filesystem UID/GID. Image build/startup validation remains outstanding.
- Helm waits are workload/hook completion checks, not database readiness guarantees for every component. No durable operations, concurrency lock, transactional rollback, retry reconciliation or supported storage expansion was introduced.
- PostgreSQL application databases/users/grants are not created. Operator-supplied pool definitions must match real SQL objects. Direct Helm users must align replica routing with topology.
- External S3 omissions can retain example chart defaults; endpoint permissions, bucket existence and object verification are not preflighted by provisioning. Existing MinIO backup-user credential rotation is still unsupported and can desynchronize WAL-G credentials.
- Raw kuberResources and standalone ingress examples retain baseline defects; they are separate manual paths, not fixed by chart changes. The Rook gitlink metadata remains incomplete.
- API input validation does not validate every possible direct Helm override. Root MinIO still interpolates credentials into ConfigMap shell text; no claim of safe arbitrary-string handling for that legacy mechanism.

## Requires Live Validation

No live cluster validation was performed. Before claiming functional completion in a deployed environment:

1. Build/start the modified images; verify initial PgCat TOML generation and projected Secret updates.
2. Install with the backend ServiceAccount in dbaas and an operator-authorized alternate namespace. Verify RBAC admission, namespace bindings, Patroni DCS access and MinIO hook completion.
3. Provision two independent releases; verify EndpointSlices, actual SQL primary/replica routing, single-pod reads and pgAdmin destinations.
4. Run a backup Job and confirm a usable object/catalog entry in MinIO; deliberately test missing target, bad credentials and WAL-G failure status.
5. Check actual PgCat exporter and Patroni scrape targets against Prometheus configuration.
6. On disposable data, run recovery preflight, execute an approved restore and verify target-time rows/timeline before exposing writes. Include backup/WAL gaps and mid-operation failures.
7. Rehearse immutable-resource migration while preserving claims/data. Test failover separately; no failover time, RPO, RTO or availability result exists here.

## Deferred to Security Phase

**Planned:** caller authentication, namespace/release authorization, tenant boundaries, supplied Secret references and credential rotation, redacted previews/subprocess errors, TLS/network policy and dependency/image reproducibility. Current previews still contain credentials and the API remains unauthenticated. No broad security-hardening claim is made.

## Deferred to Reliability Phase

**Planned:** verified isolated restore/cutover, backup retention and external copies, durable operation status/locking/reconciliation, safe SQL lifecycle/expansion procedures, topology-aware disruption/scheduling/resource policy, image/runtime integration CI and tested failure/recovery runbooks. No new operator or control-plane architecture was introduced.
