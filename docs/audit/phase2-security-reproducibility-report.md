# Phase 2 security and reproducibility report

Date: 2026-10-03. Built on the uncommitted Phase 1 working tree without discarding its fixes. No commits, pushes, cluster mutations, credential rotations or Docker image builds/runs were performed.

## Implementation plan

The pre-edit plan covered: fail-closed Bearer authentication and operator namespace scope; external Secret defaults with explicit development compatibility; sanitized previews/logs/errors and bounded subprocesses; preservation of private temporary files; exact direct dependencies/source versions and npm lock; secret scanning, examples, migration documentation and offline regression tests. No identity platform, operator, chart-family merge or reliability architecture was introduced.

## Security Issues Fixed

| Issue | Change | Principal files |
|---|---|---|
| Unauthenticated provisioning/preview | All /api/ paths require configured Bearer token; constant-time comparison; namespace allowlist | application/app/main.py, application/k8s/deploy.yaml |
| Static credential defaults and credential-bearing ConfigMaps | Password/access-key defaults cleared; existing Secrets by default; root MinIO uses Secret refs; raw manifests sanitized | Both chart families, kuberResources |
| Credential exposure in API errors/preview/logs | Recursive preview redaction including pgAdmin pass; no raw command output/context/traceback responses; validation errors omit input | FastAPI backend |
| Unsafe runtime diagnostics/files | Private Patroni YAML and watcher TOML; sanitized watcher parsing errors and chart MinIO initialization errors | patroni/entrypoint.sh, pgcat watcher/logger, MinIO templates |
| Unbounded subprocesses | Argument arrays retained, return codes checked, explicit timeouts and safe failure summaries | FastAPI, scripts/recovery.py |
| Browser authentication/credential handling | Memory-only token header; default Secret-reference payload; explicit development mode; auth failures; escaped dynamic option text; successful submit clears password fields | application/static/index.html |
| Secret-reference recovery regression risk | Preflight checks external credential keys/namespaces/workload references before mutations; Phase 1 guards retained | scripts/recovery.py |
| Local secret/build context hygiene | Ignore local credential files/caches, preserve safe examples and npm lock | .gitignore, component .dockerignore/.gitignore |

The API's namespace allowlist limits shared-operator scope; it does not implement individual user ownership. Inline input validation retains DNS-safe names, bounds and serialized PostgreSQL pool identifiers; S3 endpoint userinfo/query strings are rejected. Administrative usernames have an explicit HBA-compatible character restriction. No nonexistent PostgreSQL-version input or new SQL lifecycle operation was invented.

## Reproducibility Issues Fixed

- Patroni's unpinned Git install replaced with patroni[kubernetes]==4.0.4 and explicit PostgreSQL adapter dependency. Existing FastAPI direct pins retained; recovery PyYAML requirement recorded.
- Watcher direct versions are exact; package-lock.json includes integrity hashes; Docker uses npm ci with lifecycle scripts disabled. The lockfile is no longer ignored by Git or Docker.
- Floating runtime image references replaced with explicit version/build tags. PgCat and pgAdmin registry manifests were verified. Unavailable queried MinIO/mc/Bitnami tags were replaced with local pinned build recipes, not left as broken defaults.
- MinIO/mc source archives downloaded and their SHA-256 recorded in Dockerfiles; readonly Go modules use upstream go.mod/go.sum. Source tags and Go toolchain are explicit.
- Helm/kubectl download checksums are verified at build time. Existing WAL-G v3.0.7 URL retained; missing /commands standalone command removed, while chart init behavior remains intact.
- Six local charts have no remote dependencies; no fictitious Chart.lock was added. Unmanaged observability versions remain operator-owned.

These are reproducibility improvements, not hermetic builds or proof of vulnerability-free versions. See [version matrix](../operations/version-matrix.md) for exact pins, upstream evidence, registry findings and limits.

## Authentication Model

DBAAS_API_TOKEN comes from environment/Kubernetes Secret; missing/short configuration produces 503, missing/invalid credentials produce 401, and a forbidden namespace produces 403. All /api/ paths are protected, including names reserved for future destructive operations. Health and form/static assets are public; API documentation routes are disabled. Exact-origin CORS is opt-in; wildcard is rejected.

The browser never persists tokens to web storage or embeds credentials in URLs. TLS must be supplied by the operator. Shell recovery continues to use kubeconfig/Kubernetes authorization plus --execute, since it is not an HTTP endpoint. Detailed setup: [API security](../security/api-security.md).

## Secret Handling Model

Default values emit only external Secret references. The API accepts existingSecrets names and does not fetch password data. PostgreSQL, MinIO and pgAdmin use secretKeyRef; PgCat and WAL-G mount configuration Secrets. External PgCat configuration owns pools/routing; browser pool controls apply only to development-generated configuration.

Inline compatibility requires Helm security.allowInlineSecrets=true and, for API requests, DBAAS_ALLOW_INLINE_SECRETS=true. Static password defaults are empty. Inline values still enter Helm release history: this mode is for disposable development only. The Phase 1 unique private temporary directories, 0600 files and exception cleanup remain; concurrency tests verify separate request directories.

Migration must use new externally managed Secret names before disabling Helm-owned Secret templates, otherwise Helm can remove the old managed objects. Credential values must match the initialized databases/object store until a coordinated rotation occurs. The existing MinIO hook does not implement password rotation. See [Secret contracts/migration](../security/secrets-management.md) and the classified [inventory](../security/secret-inventory.md).

## Version Pinning Changes

PostgreSQL stays on major 16, Python on 3.12 and Node on 18. Patroni 4.x matches the existing primary role labels; upstream metadata supports the Python runtime. Pin selection does not establish what the former floating images contained. Compare deployed versions before migration and do not automatically downgrade. Historical baselines and Node 18 require a separate supported-version/security-patch review before production.

Custom dbaas/* tags designate local builds, not newly published artifacts. Build/package the changed watcher, Patroni, MinIO/mc, kubectl and backend, then override registry references as appropriate. No image was built or pulled. Apt packages, base tags, Python transitives and WAL-G artifact integrity remain reproducibility limits; trusted production builds should record immutable image digests.

## Tests Added

- Real ASGI middleware tests: missing/invalid/valid token, missing configuration, protected future destructive paths, namespace/input rejection and sanitized validation responses.
- Subprocess timeout/output redaction; unchanged safe Helm argument construction.
- Default external Secret values, rejection of unexpected raw credentials, default chart Secret refs, credential-free generated ConfigMaps and redacted previews.
- Unique private request directories/files and cleanup; external-Secret recovery preflight and missing-Secret abort before uninstall.
- npm manifest/lock consistency and integrity metadata; Docker instruction/JSON and RUN-shell checks, including lockfile inclusion in the build context.
- Browser token header, no-token/401 handling and default reference mode; real watcher --once process verifies private TOML and no malformed-YAML credential leakage.

Phase 1 tests remain and use explicit synthetic development fixtures where generated Secrets are required. This intentional fixture update does not remove the routing, namespace, backup failure, temporary cleanup or recovery assertions.

## Validation Results

```bash
PYTHONDONTWRITEBYTECODE=1 application/.venv/bin/python -m unittest discover -s tests -v
node tests/test_ui.js
PYTHONDONTWRITEBYTECODE=1 application/.venv/bin/python tests/validate_static.py
```

- **33 Python tests passed; 6 Node tests passed.**
- **Six Helm lints passed.** Tests render both families in dbaas/test-dbaas, verify release isolation and parse generated configuration. Default external and explicit development paths are exercised.
- Static runner: 43 YAML, 2 JSON, 1 TOML, 6 Python, 4 shell and 4 JavaScript checks (including inline UI). git diff --check passes. Docker checks cover instruction structure, JSON and RUN shell syntax; no BuildKit build is claimed.
- `npm ci --ignore-scripts --no-audit --no-fund`: passed, 37 packages installed. No package lifecycle scripts executed. This is not a vulnerability audit.
- Runtime source search found no floating latest image references or unpinned Patroni Git install. Remaining latest text is PostgreSQL recovery timeline syntax or documentation URLs. Secret-pattern hits are empty slots, references, variable names, test fixtures and gated development templates; no known historical password values were intentionally retained.
- ShellCheck, yamllint, kubeconform and Hadolint are unavailable. YAML parsing is not Kubernetes schema/admission validation. Docker base compatibility, CORS in a real browser, live Secret rotation and full migration require integration tests.
- Checksum-verified Gitleaks v8.24.3: `gitleaks dir --redact --config .gitleaks.toml .` and `gitleaks git --redact --config .gitleaks.toml --log-opts=--all .` both completed with no default-rule findings; history scan covered 148 reachable local commits. This does **not** establish that old low-entropy credential defaults were safe. Their source inventory and rotation requirements remain. CI configuration mirrors these commands; the CI job itself has not run.

## Remaining Security Risks

Shared operator token; no tenant ownership, rate limiting or fine-grained authorization. TLS/network policy and broad securityContext changes remain operator work. Kubernetes Secret access, node access and pod exec remain privileged. Inline Helm history, previously generated files/logs, old ConfigMaps and prior Git history may retain credentials. MinIO administrative process arguments and necessary database credential copies in consumer configs remain within the trusted container boundary. No CVE assessment or complete Git-history remediation is claimed.

## Requires Credential Rotation

If prior defaults or tracked values were deployed, rotate PostgreSQL superuser/replication credentials, PgCat pool/admin credentials, pgAdmin login, MinIO root/backup credentials and any reused object-store/AWS keys. Revoke any separately exposed API tokens. Historical validity was not tested; values are intentionally omitted. Rotation must coordinate SQL roles, Secrets, clients and backup consumers. This task did not rotate credentials or rewrite history.

## Deferred to Phase 3

Live image/startup and migration validation; isolated restore/PITR drills; tested TLS/network/storage permissions; supported-version/CVE review and artifact digests; coordinated credential rotation; durable operation status/locking; fine-grained authorization design; topology/resource/disruption policies after workload evidence. No PDB, anti-affinity, monitoring expansion, benchmark or operator implementation was added.
