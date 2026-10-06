# Smoke testing and live checks

## Disposable kind workflow

Prerequisites: Linux amd64 Docker engine, kind, kubectl, Helm, Python 3 with PyYAML (`scripts/requirements.txt`), network access to pinned image/source/package registries, sufficient local disk/memory. The harness creates a random cluster name and private kubeconfig; it never attaches to the caller's current cluster. Default node image is `kindest/node:v1.30.0`, matching the pinned kubectl era; this is a compatibility test target, not a recommendation for new production clusters. `KIND_NODE_IMAGE` can select a reviewed version; observe kubectl version-skew constraints.

```sh
bash scripts/smoke-test/build-images.sh
SKIP_BUILD=1 bash scripts/smoke-test/run.sh
# Independently opt into destructive recovery, inside that new disposable cluster only:
RUN_PITR_TEST=1 SKIP_BUILD=1 bash scripts/smoke-test/run.sh
```

Without SKIP_BUILD, the harness builds all local images. SMOKE_NAMESPACE and SMOKE_RELEASE customize test names. It creates random external Secrets via stdin, installs namespaced API RBAC and the API Deployment, calls authenticated `/api/deploy`, provisions MinIO/two Patroni members/PgCat, checks SQL roles/readiness/storage, writes test data through PgCat, creates a manual backup Job, and checks remote WAL-G backup metadata (objects fetched from S3). No secret values are printed. It cleans only its own named cluster on success/failure. It does not call legacy `init.bash`. Terminating the harness with SIGKILL may prevent cleanup; list kind clusters and remove only the exact printed smoke name after inspection.

See [Phase 4 runtime validation](runtime-validation.md) for evidence collection, the inotify prerequisite, controlled failure flags and measured limitations.

Optional PITR records a UTC target after the base backup, writes a second marker, switches WAL, uses existing destructive recovery in that disposable cluster, and checks only the first marker remains. Phase 4 exercises this path with explicit data assertions; a base-backup listing alone is not a restore/WAL-coverage test. The smoke namespace itself is deleted with the disposable cluster, including Secrets and volumes. No chaos test is run by default.

## Read-only checks against an existing test cluster

Use a reviewed kubeconfig/context. All wrappers require namespace and the **Patroni Helm release**. PgCat/cluster checks also require the PgCat release:

```sh
bash scripts/validate/cluster-health.sh --namespace test-db --release team-patroni --pgcat-release team-pgcat
bash scripts/validate/patroni-health.sh --namespace test-db --release team-patroni
bash scripts/validate/pgcat-health.sh --namespace test-db --release team-patroni --pgcat-release team-pgcat
bash scripts/validate/backup-health.sh --namespace test-db --release team-patroni
bash scripts/validate/storage-health.sh --namespace test-db --release team-patroni
```

Scripts exit nonzero for missing/unready members, role mismatch, failed proxy queries, missing/unbound claims or absent remote backup metadata as applicable. Backup check does not prove freshness, integrity or PITR. Metrics/availability benchmarks are outside this smoke test.

## Phase 4 failure-test entrypoints

`bash scripts/smoke-test/failure-test.sh ACTION NAMESPACE PATRONI_RELEASE [PGCAT_RELEASE]` prints a planned command by default. Supported actions: `primary-delete`, `replica-delete`, `pgcat-restart`, `backup-during-workload`, `recovery`. Mutations require explicit `RUN_FAILURE_TEST=1`; no experiments were run in Phase 3. Phase 4 uses the disposable harness for measured experiments. Replica deletion requires exactly one selected replica to prevent ambiguous targeting.

Prerequisites: disposable/test cluster approval, healthy multi-node placement, verified backup and separate restore, continuous workload with durable transaction IDs, synchronized timestamps, client reconnect policy, role/lag/endpoint collection, and a prewritten abort/cleanup plan. Direct deletion bypasses PDBs; it is not a node-drain test. Recovery uses its separate dry-run/execute safeguards. Workload generation and measurement methodology remain Phase 4 work.

## Offline validation

```sh
PYTHONDONTWRITEBYTECODE=1 application/.venv/bin/python -m unittest discover -s tests -v
node tests/test_ui.js
node tests/test_pgcat_health.js
python3 tests/validate_static.py
```

See [Phase 3 report](../audit/phase3-reliability-report.md) for actual build/smoke outcomes. Never convert a successful render or build into a live reliability claim.
