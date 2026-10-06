# Phase 3 reliability report

## Pre-edit implementation plan

| Workload | Current behavior / failure mode | Proposed fix | Stateful-system risk | Validation |
|---|---|---|---|---|
| Patroni/PostgreSQL | Readiness only, default rolling update, no resources/spreading/PDB | Configurable resources; database-aware readiness/startup; optional loop liveness; longer grace; preferred node separation; OnDelete upgrade policy; multi-pod maxUnavailable=1 | Restores can outlive startup windows; no primary-aware rollout; memory limits need workload tuning | Render single/2/3-pod profiles; test scoped selectors; document manual upgrades |
| PgCat/watcher | Config init gate exists; no query readiness/resources/disruption controls | Watcher executes real SQL probe through local proxy; configurable resources, preferred spread, conditional PDB and grace | Probe verifies one configured pool; drain timeout must fit grace; per-pod config stays private | Unit/mock probe tests, renders, image build/smoke attempt |
| MinIO | Single-server storage; no probes/resources/retention declaration | Documented health probes; requests/optional limits; explicit single-instance restriction and retained claims | Multiple independent servers behind one Service would corrupt storage assumptions; no distributed redesign | Render and invalid replica tests; smoke attempt |
| Backup | Correct target/error propagation; no concurrency/deadline controls | Forbid overlap, bounded configurable deadlines/history/TTL, remote command timeout, resources | Stopping kubectl alone does not necessarily stop remote backup; long databases need longer budget | Render and shell regressions |
| FastAPI | One replica, basic health, synchronous Helm operations | Dependency/config readiness, resource requests, long grace and bounded Uvicorn shutdown; keep one replica | No distributed operation locking; scaling out still unsafe | ASGI tests and deployment checks |
| Recovery | Explicit destructive mode/preflight; no retained failure instructions | Safe state journal, phase tracking and operator instructions; retain selected values only in explicit private state directory | No transaction; deletion is irreversible; journal must not expose credentials | Failure injection before/after deletion, dry-run tests |
| Network/storage | No enforced network policy; PVC templates immutable | Opt-in explicit NetworkPolicy rules; configurable scheduling/access modes and optional Retain policy | CNI/API/S3 destinations unknown; storage class/size changes require migration | Default policy absent, fail-closed opt-in configuration, migration guide |
| Builds/test tooling | Pinned recipes, no actual build/smoke evidence | Attempt all controlled builds; isolated kind harness, read-only validation and Phase 4 preparation | Never reuse/delete an existing cluster; PITR only explicit opt-in | Build logs, offline harness checks, disposable smoke attempt |

Plan recorded before Phase 3 runtime edits. Existing Phase 1/2 work is retained. Both Helm families are active; raw kuberResources remains legacy. Observability components are externally installed and receive documentation only.

# Reliability Improvements

Implemented on 2026-10-03, preserving the uncommitted Phase 1/2 tree. Baseline rerun: 33 Python tests and 6 Node tests passed before runtime edits. Active paths are both Helm families, Patroni image/entrypoint, PgCat watcher, API, WAL-G/MinIO/client/kubectl recipes and deployment/recovery scripts. Raw `kuberResources/` is legacy. Monitoring/logging installations remain operator-owned.

All chart containers now expose resource requests/limits. PgCat readiness executes bounded SQL, API has separate local-dependency readiness, database startup has a restore-aware window, and backup/recovery operations have clearer bounded behavior. See [reliability design](../operations/reliability.md) for default values and tradeoffs.

# Kubernetes Hardening

Conditional PDBs, workload scheduling helpers, optional scoped NetworkPolicies, namespaced API NetworkPolicy RBAC, longer termination grace and configurable Retain/Retain policy were added. NetworkPolicy is disabled until operators supply ingress/egress flows. No network isolation or CNI enforcement is claimed. API stays at one replica because operation coordination is not durable/distributed.

# Scheduling Model

Preferred hostname anti-affinity for PostgreSQL and PgCat; required/none modes configurable. Explicit affinity overrides the generated rule. Node selectors and tolerations are configurable. Optional topology constraints receive workload/release-specific selectors; zone labels are not assumed. PDB maxUnavailable=1 exists only above one replica; it does not establish a database quorum or protect direct deletions/controller rollouts. Single-node labs remain schedulable; no single-instance HA claim.

# Probe Model

Patroni startup `/health`, readiness `/read-only`, optional `/liveness` disabled by default. Startup allows 360 ten-second attempts; operators must extend/disable it for longer restores. PgCat's watcher checks SELECT 1 through the local proxy with the first pool/user; it does not prove every shard. MinIO uses documented live/ready endpoints. pgAdmin uses `/misc/ping`. API `/readyz` checks token configuration and local tools/charts, while `/healthz` is process health. Jobs use completion/deadlines rather than probes.

A built-image inspection found inherited **SIGINT** from the PostgreSQL base image; Patroni's installed handler registers **SIGTERM**. `patroni/Dockerfile` now explicitly sets SIGTERM, and the rebuilt image reports that setting. PgCat's pinned upstream source/image uses SIGINT for graceful drain and SIGTERM for immediate exit. No competing Patroni preStop/switchover script was introduced. Shutdown behavior under real traffic remains unmeasured.

# Storage Safety

PVC/controller selectors, claim names and governing Services are preserved from Phase 1/2. PostgreSQL/MinIO default OnDelete; PostgreSQL explicitly keeps OrderedReady. Normal retention remains Kubernetes default Retain, with optional explicit Retain/Retain gated to Kubernetes >=1.27. Access modes/class/capacity are configurable for new deployments; existing template changes need review. MinIO rejects replica counts other than one because it is a single-server configuration. [Storage guide](../operations/storage.md).

# Backup Reliability

Forbid concurrency; success/failure history 1/3; starting deadline 3600 seconds; Job deadline 21600 seconds; remote GNU timeout 21000 seconds with a 60-second forced-kill window; TTL 86400 seconds. All configurable, preserving backoffLimit=1 and OnFailure. Rendering rejects a remote timeout that does not fit inside the configured Job budget. The remote timeout bounds a WAL-G command even if kubectl disconnects; retries and abrupt control-plane failures still require inspection for lingering exec processes. Forbid does not prevent manually launched overlapping Jobs or backups on different primaries. WAL-G resources are charged to the PostgreSQL container. No actual backup has passed this smoke test.

# Recovery Reliability

Existing ownership, exact-PVC UID, consumers, backup metadata and deterministic ordering safeguards remain. Stages are journaled, including before destructive calls. CLI execution requires a new `--state-dir`; values/state are private and retained after failure by explicit opt-in. Failed destructive stages warn that data may already be deleted and print exact reviewed reinstall commands (Patroni before PgCat). Default dry-run temporary values are cleaned. There is no automatic rollback and no transaction. Failure injection validates retained state, permissions, diagnostics and cleanup. [Migration and compatibility changes](../operations/migration-phase3.md).

# Image Build Results

**BUILD VALIDATED** — all seven final controlled recipes built on the local amd64 Docker 29.4.3 engine:

| Image | Result | Additional evidence |
|---|---|---|
| dbaas/patroni:2.1.0 | Built; rebuilt after stop-signal correction | Installed Patroni signal handler inspected; final StopSignal=SIGTERM |
| dbaas/pgcat-config-watcher:1.1.0 | Built; rebuilt with js-yaml 4.3.2 | Docker npm ci succeeded; SQL client installed |
| dbaas/backend:0.2.0 | Built | All three bundled charts linted inside image using the smoke payload; API started in kind |
| dbaas/wal-g:3.0.7 | Built | Binary reports v3.0.7 |
| dbaas/minio:RELEASE.2025-04-22T22-12-26Z | Built | Source archive SHA-256 verified; binary --version runs |
| dbaas/mc:RELEASE.2025-04-16T18-13-26Z | Built | Source archive SHA-256 verified; binary --version runs |
| dbaas/kubectl:1.30.0 | Built | Publisher checksum verified; binary reports v1.30.0 |

Initial WAL-G/MinIO/mc/kubectl recipes failed downloading Bullseye security packages (HTTP 404). Utility runtimes moved from pinned Debian 11.11-slim to 12.9-slim, then all four retries passed. MinIO source builds report DEVELOPMENT.GOGET because release linker metadata is not injected; the source tag/checksum and image recipe identify the selected code. This is documented, not presented as an upstream release binary.

Host npm ci initially failed in offline mode because its cache was incomplete. Online npm ci restored 37 locked packages. npm audit exposed high-severity js-yaml parsing advisories; the exact pin/lock moved from 4.1.0 to 4.3.2 after checking the upstream release. Final npm ci reports **zero vulnerabilities** for that dependency set. No broad forced dependency upgrade was used.

These are local artifacts, not registry publications. Full image vulnerability scanning, immutable promotion digests, WAL-G publisher-archive checksum verification and supported-version upgrades remain future work. Buildability does not prove runtime data safety. Local transient build logs are `/tmp/dbaas-phase3-builds/`; do not rely on those paths as durable CI artifacts.

# Smoke Test Results

Three non-destructive disposable kind attempts were made, with unique names:

- `dbaas-smoke-7706094b15`
- `dbaas-smoke-5031c088a4`
- `dbaas-smoke-5f8f822fe9`

All were cleaned up; `kind get clusters` afterward showed only the pre-existing `kind` cluster. No pre-existing cluster was mutated. No PITR or failure experiment was enabled.

**SMOKE VALIDATED** — limited to disposable cluster creation, local image loading, namespace/Secret/RBAC preparation, API Deployment readiness, localhost port-forward and authenticated API request. These are intermediate harness steps, not a passing end-to-end smoke test.

**NOT YET VALIDATED** — full provisioning/SQL/backup/recovery. The final diagnostic from Helm inside the API pod was:

```text
Kubernetes cluster unreachable: Get "https://10.96.0.1:443/version": EOF
```

The API returned HTTP 400 with no completed releases; only the backend pod was present. All generated charts lint inside the same API image, so the recorded blocker is in-cluster API connectivity, not a Helm syntax error. Its underlying CNI/host-network cause is unresolved; no API bypass or privileged networking workaround was introduced to conceal it.

**LIVE CLUSTER VALIDATED** — no existing/production cluster validation or database lifecycle validation. Only the disposable infrastructure/API steps above were exercised.

The harness implements later membership/SQL/storage/backup-object assertions and explicit RUN_PITR_TEST=1 data assertions, but those branches remain Experimental until a complete run succeeds. [Usage and prerequisites](../testing/smoke-testing.md). Smoke logs were retained locally at `/tmp/dbaas-phase3-smoke*.log` with bounded diagnostics.

# Static Validation Results

**STATICALLY VALIDATED**:

- Python unittest: **46 tests passed** (33 prior tests plus 13 reliability regressions).
- Node: **6 UI/watcher tests passed**, plus **4 SQL readiness cases passed**.
- Helm lint: **6 charts passed**; unittest renders cover both families, replica counts 1/2/3, namespace/release isolation, PDBs, preferred/required affinity, topology selectors, resource overrides, probes, retention version gate and NetworkPolicy opt-in/error cases.
- Static parsers: **43 YAML, 2 JSON, 1 TOML, 9 Python, 13 shell, 6 JavaScript checks** (includes inline UI JavaScript). Rendered YAML parsing is additionally part of the unit suite.
- Docker instruction/JSON/RUN-shell syntax checks passed as part of the suite.
- npm ci: **37 packages installed**, final audit **0 vulnerabilities**.
- Gitleaks v8.24.3: working tree **0 findings**; all reachable Git history **148 commits, 0 findings**. This does not revoke earlier advice to rotate any previously exposed low-entropy example credentials.
- `git diff --check`: passed.
- Mermaid CLI is unavailable: four `.mmd` sources and `scripts/render-diagrams.sh` supplied; SVG rendering is **NOT YET VALIDATED**. No fabricated screenshots or metrics.
- ShellCheck, kubeconform, yamllint and Hadolint unavailable; available parser/shell syntax/Helm checks are recorded above, not substituted claims of schema/live validation.

# Immutable-Field Migration Risks

No default Phase 1/2 selector/claim identity changes. Existing pre-Phase-1 resources may still have immutable selector/serviceName mismatches. Overriding volumeClaimTemplates class/size/accessModes or an existing nondefault podManagementPolicy needs controlled migration. Service selectors are mutable but routing-sensitive; clusterIP/headless changes may require recreation. OnDelete means Helm success does not imply existing pods run the new template. See [migration](../operations/migration-phase3.md) and [upgrades](../operations/upgrades.md).

# Remaining Single Points of Failure

Single-instance MinIO and its volume, default one PgCat pod, one API pod without durable operation state/locking, single-node lab control plane/node/storage, and any single PostgreSQL API profile. Optional additional PgCat/Patroni members do not remove storage/control-plane failure domains. External S3, tested multi-node storage and operator-managed Kubernetes HA remain deployment responsibilities.

# Not Yet Live Validated

PostgreSQL bootstrap, streaming replication, role-Service routing, multi-pod PgCat, actual SQL readiness under load, controlled shutdown, eviction/PDB behavior, topology placement, CSI retention/expansion, NetworkPolicy enforcement, backup object creation, WAL continuity, restore target accuracy, and data consistency after failure. No benchmark, RPO, RTO, failover-time or availability result is asserted.

# Deferred to Phase 4

Resolve the disposable cluster's pod→Kubernetes Service connectivity and complete smoke/PITR assertions first. Then execute reviewed primary/replica deletion, PgCat restart and backup-under-workload experiments with durable transaction IDs, lag/endpoint evidence and client reconnection measurements. Test planned switchover, drain admission, storage failures, recovery failure injection and long-restore windows. Add durable operation locking/job state before scaling the API; add image CVE/support review and reproducible artifact promotion before production consideration.

# Files Changed in Phase 3

| Group | Files |
|---|---|
| Helm | Both families: all three values.yaml, scheduling helpers, PDB/NetworkPolicy templates, Patroni/backup, proxy/pgAdmin and MinIO workload templates |
| PostgreSQL/Patroni | patroni/Dockerfile (explicit stop signal); chart probes/resources/update/storage/scheduling |
| PgCat | pgcat/pgcat-health.js; Dockerfile; package.json/package-lock.json; proxy readiness/resources |
| FastAPI | application/app/main.py readiness; application/k8s/deploy.yaml resources/probes/grace; rbac.yaml optional policy lifecycle |
| Backup | Both backup CronJob templates and values |
| Recovery | scripts/recovery.py private retained workspace, phase journal, explicit CLI requirement and failure instructions |
| Docker | patroni, pgcat, WAL-G, MinIO/mc and kubectl recipes; backend recipe preserved from Phase 2 and built with bundled changes |
| Test Harness | scripts/smoke-test/*, scripts/validate/*, tests/test_reliability.py, tests/test_pgcat_health.js; Docker syntax test recognizes STOPSIGNAL |
| Documentation | Five operations/testing guides, four Mermaid sources, render script, Phase 3 report; README/application README, version matrix and audit-context updates |

No commit, push, production deployment, destructive PITR or chaos experiment was performed.
