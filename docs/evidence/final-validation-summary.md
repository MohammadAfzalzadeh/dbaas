# Final validation summary

Phase 6 performs local reproducibility and packaging checks. It adds **no live failure experiment**, destructive PITR or new benchmark. The [capability index](README.md) retains historical live scope and failed attempts.

## Current Phase 6 checks

| Check | Exact result | Evidence |
|---|---|---|
| Fresh Python environment | 79 tests passed | [Python log](../../results/validation/phase6/python-tests.txt) |
| Node regressions | 7 tests passed | [Node log](../../results/validation/phase6/node-tests.txt) |
| PgCat SQL readiness | 4 cases passed | [Readiness log](../../results/validation/phase6/pgcat-readiness.txt) |
| Helm lint | 6 charts passed | [Static checks](../../results/validation/phase6/static-checks.txt) |
| Helm template and rendered YAML parse | 6 charts; 48 rendered documents | [Render counts](../../results/validation/phase6/helm-template.json) |
| Image builds | 7 recipes passed | [Build log](../../results/validation/phase6/image-builds.txt) |
| npm ci | Locked offline install passed | [Install log](../../results/validation/phase6/npm-ci.txt) |
| Mermaid | 20 sources rendered to 20 SVG + 20 high-resolution PNG | [Catalog](../architecture/README.md) |
| Final measured charts | 8 SVG + 8 PNG generated from preserved data | [Source manifest](../images/results/final/manifest.json) |
| Documentation | All checked internal links and Markdown anchors passed; exact counts in JSON | [Link check](../../results/validation/phase6/documentation-links.json) |
| Historical evidence preservation | 419 pre-existing result files unchanged by SHA-256 | [Verification](../../results/validation/phase6/preservation.json) |
| Security | Worktree, all Git history, generated results and report scans found no leaks | [Security summary](../../results/validation/phase6/security-summary.json) |

[Machine-readable final summary](../../results/validation/phase6/summary.json) records parser counts and validation scope. Syntax checks use Python AST, YAML/JSON/TOML parsers, `bash -n`, `node --check`, Helm and `git diff --check`; they are not a cluster-side Kubernetes schema validation or an image vulnerability scan.

## Reproducibility commands and limits

Run the root README's local checks from the repository root with Python 3.11 or later. This phase created a fresh temporary virtual environment and installed `application/app/requirements.txt` and `scripts/requirements.txt`. npm used the lockfile and an existing local cache; an empty-cache network install was not separately tested. BuildKit could reuse local layers; the seven image builds do not claim a cold-cache or cross-architecture build. No release was published.

```sh
python3 -m venv /tmp/dbaas-phase6-check
/tmp/dbaas-phase6-check/bin/pip install -r application/app/requirements.txt -r scripts/requirements.txt
/tmp/dbaas-phase6-check/bin/python -m unittest discover -s tests
npm ci --offline --cache /tmp/dbaas-npm-phase3 --prefix pgcat
node tests/test_ui.js
node tests/test_pgcat_health.js
/tmp/dbaas-phase6-check/bin/python tests/validate_static.py
bash scripts/smoke-test/build-images.sh
python3 tools/reporting/check-links.py
```

Explicit `helm template phase6 CHART --namespace phase6` was run for each of the three charts in each chart family, and every rendered document was parsed as YAML. No cluster resources were applied. Diagram generation initially hit a Mermaid label parse error and a browser sandbox restriction; the corrected source rendered with the local browser. Those packaging failures are separate from runtime findings.

## Historical checks — not rerun or added to current counts

| Evidence period | Result | Boundary |
|---|---|---|
| Phase 4 final live suite | 13 PASS, 2 NOT APPLICABLE | [Original validation](../../results/runtime/logs/validation.json); earlier failed attempts retained separately |
| Initial Phase 5 | Primary and replica drains exercised; abrupt-loss replica convergence FAILED | [Initial artifacts](../../results/runtime/multinode/dbaas-phase5-8a3ad9f385/); no synthetic aggregate pass total |
| Phase 5 continuation automatic recovery | 3 clean runs converged without reinitialize | [Windows](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json); does not resolve historical cause |
| Continuation alert rehearsal | 4 conditions completed transitions across distinct attempts | Proxy in attempt 1, database/leader in attempt 2, backup in attempt 3; [index](phase5-continuation.md) |
| Continuation scrape-fault alert | 1 failed attempt | Pending not observed within bound; [failure](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/metrics-alert/attempt-1/failure.txt) |
| Prometheus regression | 1 rule scenario, stopped and healthy scopes | [Historical result](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/promtool/attempt-1/result.json); not rerun in Phase 6 |
| Final benchmark matrix | 24 complete samples; 0 reported failed transactions | [Final matrix](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/pgbench.json); aborted/earlier samples excluded |
| Backup impact | 1 baseline/during pair | [Pair](../../results/benchmarks/dbaas-phase5-bc4cacdf48/matrix/attempt-1/backup-impact.json); not repeated trials |
| Restore sizes | 2 successful size samples | [Performance report](../report/performance-results.md); no scaling or off-site guarantee |
| Monitoring harness follow-up | 79 Python tests, including 5 new failure-path regressions | [Original summary](../../results/validation/monitoring-harness/attempt-1/summary.json); no live rerun |

Initial replica result: **FAILED**. Final classification: **UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS**. Seven scrape targets remain broken. External/off-site recovery, replication credential rotation and notification delivery remain **NOT VALIDATED**.

## Security interpretation

Gitleaks uses redaction and the repository configuration. The final review covers tracked and untracked files, preserved runtime evidence, reports and generated image/chart metadata. The history scan covers 148 commits. A separate tracked-file search records locations of credential-related fields without printing values; field names and Secret references are not classified as leaks. No real credentials were intentionally added. These scans do not prove the absence of every possible secret or replace dependency/image vulnerability assessment.

## Scope and repository state

Changes in this phase are documentation, Mermaid sources/exports, measured reporting tools, link validation and new Phase 6 validation artifacts. Existing chart paths and runtime behavior remain intact. Prior uncommitted work is preserved. No commit, push, deployment or publication was performed.
