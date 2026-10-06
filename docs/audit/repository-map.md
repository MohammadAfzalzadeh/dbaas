# Repository map

> Phase 6 navigation: this document retains its historical audit scope. For current classifications and remaining risks, use the [authoritative evidence index](../evidence/README.md) and [production gap analysis](../report/production-gap-analysis.md).

> Phase 3 update (2026-10-03): [reliability report](phase3-reliability-report.md) supersedes baseline findings about resource requests, probes, scheduling/PDBs, shutdown, backup deadlines and build validation. Both chart families now implement those controls; live provisioning remains blocked by the recorded in-cluster API connection failure. Earlier sections retain their dated audit evidence.

> Phase 2 update (2026-10-03): the [security and reproducibility report](phase2-security-reproducibility-report.md) supersedes earlier authentication, credential-default, preview/logging and dependency findings. Default chart/API input now uses external Secrets; inline values require development opt-in. Phase 1 behavior remains covered by regression tests. Earlier sections preserve their dated evidence.

Audit date: 2026-10-01. Source revision: `c275fc2dd3c4e8e9db1e28eadf50100e3cfcbbc1`. Branch at inspection: `feat/dbaas-application`; clean before audit. The baseline index contained 77 entries, including a gitlink and a research PDF. Phase 1 working-tree additions are included below; see the [correctness report](phase1-correctness-report.md). This map covers the repository's implementation surfaces; ignored virtual environments are local tooling, not shipped source.

## Paths and responsibilities

| Path | Contents / role | Actual consumer / boundary |
|---|---|---|
| [`application/app/main.py`](../../application/app/main.py) | FastAPI models, UI serving, values preview, Helm deployment orchestration, error/log handling | HTTP control surface; no inventory database or reconciliation worker |
| [`application/app/templates/`](../../application/app/templates) | Three Jinja templates converting request objects into Helm values | Shared `build_context()`/`generated_values()` for preview and deploy |
| [`application/static/index.html`](../../application/static/index.html) | Browser form, validation, dynamic database/user/access controls, submit handlers | Served by module-relative `home()` and static mount; one submit handler |
| [`application/app/requirements.txt`](../../application/app/requirements.txt) | Pinned direct Python packages | Application Docker build |
| [`application/Dockerfile`](../../application/Dockerfile) | Python 3.12 image, Helm 3.15.4, kubectl 1.30.0, app/charts, UID 10001 | Builds HTTP provisioning service; image deployment manifest is still a registry placeholder |
| [`application/k8s/`](../../application/k8s) | Backend Deployment/Service, Role/ServiceAccount/RoleBinding, Ingress | Manual backend installation in `dbaas`; ingress assumes Traefik and cert-manager |
| [`application/helmCharts/`](../../application/helmCharts) | MinIO, Patroni, PgCat charts bundled in backend image | Default image path `/app/helmCharts`; selected by `find_chart()` |
| [`helmCharts/`](../../helmCharts) | Root MinIO, Patroni, PgCat charts | `init.bash`, deployment and recovery scripts, manual Helm; can also be selected by API chart discovery |
| [`patroni/`](../../patroni) | PostgreSQL-based image and configuration-generating entrypoint | Chart default references published custom image; build provenance not established |
| [`pgcat/`](../../pgcat) | Watcher Dockerfile, JS YAML→TOML generator and file watcher, Winston logging | Init generation with `--once`, then sidecar beside PgCat; atomic TOML writes to shared emptyDir |
| [`wal-g/Dockerfile`](../../wal-g/Dockerfile) | Downloads WAL-G v3.0.7 amd64 binary | Init container copies binary into shared volume; archive/backup/restore run inside Patroni container |
| [`kuberResources/`](../../kuberResources) | Raw Patroni, recovery Patroni, DB Services, PgCat, MinIO, backup CronJob | Earlier/manual deployment path with different names, defaults, and correctness issues; not applied by `deploy.sh` |
| [`scripts/deploy.sh`](../../scripts/deploy.sh) | Sequential Helm deployment with wait/failure checks | Root charts; namespace flag defaults dbaas; paths anchored to script |
| [`scripts/ptr_recovery.sh`](../../scripts/ptr_recovery.sh) | Wrapper for Python preflight and explicit in-place recovery | Root charts; namespace defaults dbaas; dry-run default, --execute required |
| [`scripts/rawfile-localpv.yaml`](../../scripts/rawfile-localpv.yaml) | OpenEBS local StorageClass declaration | Needs external provisioner; charts default to `standard`, so this is not automatically selected |
| [`init.bash`](../../init.bash) | Delete/recreate kind cluster, build/load images, install three root charts | Lab bootstrap; destroys named kind cluster; built image names differ from several chart defaults |
| [`kind/kind-config.yaml`](../../kind/kind-config.yaml) | One control-plane and two worker nodes | kind lab topology; not an HA Kubernetes control plane |
| [`serviceMonitor/`](../../serviceMonitor) | Patroni, PgCat, MinIO ServiceMonitors; Patroni/PgCat target release-scoped chart Services | Assumes Prometheus Operator CRDs and `kube-prometheus-stack` selection labels |
| [`log/`](../../log) | Loki/Grafana persistence values, Fluent Bit output/input values, Grafana Loki datasource values | External charts must be chosen and installed separately; versions not declared |
| [`ingress/`](../../ingress) | Traefik IngressRoutes for MinIO, pgAdmin, Grafana | External Traefik prerequisite; plain `web` entrypoint; pgAdmin service name differs from chart-generated name |
| [`rook-config/values.yaml`](../../rook-config/values.yaml) | Rook operator and CSI values | No CephCluster/pool/storage deployment workflow is supplied here |
| `rook-config/rook` | Git index entry mode `160000`, commit `baf0612588f7a7c6436e4d34b8e227dcbb56d83e` | Missing `.gitmodules` mapping; `git submodule status` fails. Not an inspected, reproducibly available Rook checkout |
| [`README.md`](../../README.md), [`application/README.md`](../../application/README.md) | GitLab starter README content | Do not currently explain actual architecture or operations |
| [`CHANGELOG`](../../CHANGELOG) | Early feature note mentioning Docker Compose | No tracked Compose file found; do not treat the note as current implementation |
| [`LICENSE`](../../LICENSE) | Apache 2.0 license text | Repository license; image/software dependencies have their own licenses |
| `پروژه کارشناسی.pdf` | Research document | Text extraction succeeds but has damaged glyph mapping; not reliable evidence of current runtime results |
| `.gitignore`, application/pgcat ignore files | Ignore local values, environments/caches, node modules, and PgCat lockfile | Root ignores `Test/*`; Phase 1 adds tests/; no CI pipeline supplied |

## Entry points

| Entry point | What it actually runs |
|---|---|
| Backend container | `uvicorn app.main:app --host=0.0.0.0 --port=8000` from `/app` |
| Browser | `GET /` → form → `POST /api/deploy`; output shown as text |
| Values preview | `POST /api/values/preview`; API-only path in current UI |
| Patroni container | `/bin/bash /entrypoint.sh` → generated `patroni.yml` → Python Patroni process |
| PgCat watcher | `node pgcat-config-watcher.js` |
| WAL-G image standalone | Docker ENTRYPOINT/CMD compose awkwardly as nested Bash; normal charts override command explicitly. Standalone execution needs verification |
| Lab setup | `init.bash`; unsafe to run against a kind cluster containing wanted data |
| Script deployment | `scripts/deploy.sh`; works independently of caller directory |
| Script recovery | `scripts/ptr_recovery.sh` → `scripts/recovery.py`; inspect by default, explicit execute mutates |

## Chart lookup and drift

`find_chart(component)` checks an explicit CHART override (invalid paths fail), container charts, module-relative bundled charts, current-directory charts, ancestors and archives. Paths are resolved at import. Static assets use module-relative paths.

| Chart | Current implementation | Remaining drift / limit |
|---|---|---|
| Root MinIO | Release selectors, matching governing Service, initialization hook; supports rootPassword and legacy rootPasword | Credentials still interpolated into ConfigMap; secret redesign deferred |
| App MinIO | Release selectors, matching governing Service, Secret and initialization hook | Existing backup-user password is not rotated |
| Both Patroni | Namespace-aware RBAC, optional bypass cluster privileges, matching headless Service, fail-closed backup shell, selected restore backup | Different stored image paths; families remain separate |
| Both PgCat | Standard values.yaml, release-derived hosts, scoped proxy/pgAdmin names/selectors, configured metrics port, watcher init container | App retains legacy pgcat-values.yaml; published watcher image must be rebuilt; ingress requires opt-in unique host |

New [scripts/recovery.py](../../scripts/recovery.py) requires Python 3 and PyYAML plus Helm/kubectl; validates live ownership and backup metadata before explicit in-place deletion. [tests/test_phase1.py](../../tests/test_phase1.py) and [tests/test_ui.js](../../tests/test_ui.js) run offline checks.

All chart metadata uses version `0.0.1` and appVersion `1.21.6`; PgCat's chart name is incorrectly `patroni-chart`. These appVersions do not establish the PostgreSQL/Patroni/MinIO/PgCat runtime versions. No chart dependencies, lockfiles, values schemas, helpers, or Helm test hooks are supplied.

**Assessment:** two intentional caller paths are visible, but the duplicated templates and uneven fixes are technical debt consistent with a partial migration. There is no documented design requiring independently maintained implementations. Consolidation is **Planned** work, and must retain CLI paths, existing release names, Secret keys, PVC identity, and old `rootPasword` compatibility during migration.

## Namespace map

| Surface | Namespace behavior |
|---|---|
| UI / API | User-selected; API defaults to `dbaas` |
| Backend installation / Role | Explicit `dbaas` |
| API Helm commands | Requested namespace, pre-created by operator with provisioning RoleBinding |
| `deploy.sh` | `--namespace`, default dbaas; operator CLI can create namespace |
| `init.bash` | No `-n`; Helm's current/default namespace context |
| `ptr_recovery.sh` | Explicit namespace for reads/mutations, default dbaas |
| Root Patroni cluster binding | Optional bypass only; subject uses release namespace, cluster names include namespace hash |
| App Patroni cluster binding | Uses `.Release.Namespace` |
| Most chart resources | No `metadata.namespace`; installed into Helm release namespace |
| Chart RoleBinding subjects | Use .Release.Namespace explicitly |
| Raw manifests | Mostly omit namespace and rely on caller context |
| ServiceMonitors | Live in `monitoring`, select Services in `dbaas` |
| PgCat/Patroni metrics Services | Defined within release charts, select only their release and component/role |
| Logging values | Point to Loki in `logging`; no namespace bootstrap in repository |
| Ingress | Raw MinIO/pgAdmin in `dbaas`, Grafana in `monitoring`; chart pgAdmin in release namespace |

Moving a cluster to a custom namespace requires changes to observability selection and permissions as well as Helm flags. Namespace choice alone does not implement tenant isolation.

## Evidence boundaries

No cluster credentials were used, workloads deployed, images pulled/built or backups changed during audit/Phase 1. Helm lint/template ran locally; application deployment and recovery commands were mocked. Chart renders and mock execution happened in memory. No benchmark, RPO/RTO, failover, or availability measurement is established. Mermaid source is embedded in the [technical audit](technical-audit.md); image export was skipped to honor the restriction to these four Markdown outputs.
