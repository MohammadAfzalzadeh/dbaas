# Phase 6.5 validation record

Review date: 2026-10-04. All results below were produced during this review. Earlier results informed claim verification but were not substituted for these reruns.

## Static and clean-candidate checks

| Check | Result | Artifact |
|---|---|---|
| Python final candidate | 86 tests passed | [Final Python](../../results/validation/phase6-5/final-python.txt) |
| Python corrected clean copy | 86 tests passed | [Clean Python](../../results/validation/phase6-5/final-clean-python.txt) |
| Node/UI/watcher | 7 passed | [Node](../../results/validation/phase6-5/final-node.txt) |
| SQL readiness | 4 passed | [Readiness](../../results/validation/phase6-5/final-readiness.txt) |
| npm ci with fresh cache/config | 37 packages installed; reported 0 audit findings | [npm](../../results/validation/phase6-5/clean-npm.txt) |
| Helm lint | 6 charts passed | [Static](../../results/validation/phase6-5/final-static.txt) |
| Helm adversarial rendering | 90 combinations; 6 collision comparisons; no accepted invalid replicas/ports after correction | [Matrix](../../results/validation/phase6-5/helm-adversarial-corrected.json) |
| Corrected clean-copy image builds | All 7 succeeded, cache allowed | [Build log](../../results/validation/phase6-5/final-clean-builds.txt) |
| YAML/JSON/Python/shell/JavaScript/TOML | Parsed; exact file counts in log | [Static](../../results/validation/phase6-5/final-static.txt) |
| Internal Markdown links | Final result and exact count in JSON | [Links](../../results/validation/phase6-5/final-links.json) |
| Gitleaks working tree/history | Final default-rule results in logs; historical low-entropy candidates remain a separate review concern | [Working tree](../../results/validation/phase6-5/final-gitleaks-worktree.txt), [history](../../results/validation/phase6-5/final-gitleaks-history.txt) |
| Historical evidence integrity | 421 pre-review result files unchanged | [Hash comparison](../../results/validation/phase6-5/historical-evidence-integrity.json) |

Baseline clean-copy Python ran 79 tests before the seven new regression methods; final count is 86, not 165 distinct tests. The image logs record builds, not vulnerability scans. The schema matrix includes both meaningful and irrelevant overrides; 90 combinations does not mean 90 invalid-input regressions.

The archive-only validator failed because it uses git ls-files. Initializing empty Git metadata enabled clean-copy validation. A future real checkout must include the currently untracked candidate files. No commit or push was made. No dependency upgrades or runtime image changes were introduced in this review.

## Live review

Owned lab: dbaas-review-ab5e7581, three kind nodes on one host, Calico enforcing CNI. Database A/B each had one PostgreSQL member; this phase validates isolation, not a new three-member failover experiment.

- Two simultaneous different-name provisions succeeded; isolated private values files were observed.
- Ten SQL connections per release returned only its marker before later restore data was inserted.
- Serial duplicate calls upgraded; concurrent same-name calls yielded one success/one failure.
- Partial PgCat failure preserved completed MinIO/PostgreSQL releases; another request succeeded and corrected retry recovered.
- Six backup scenarios: two success controls and four failures, with no false catalog records and cluster B preserved.
- Three live negative PITR dry runs rejected; six simulated precondition cases plus a past-unarchived-target boundary case are explicitly separated from live tests.
- One isolated target-time restore preserved source and separate PVC identity.
- Four prohibited network paths timed out; positive SQL/DNS/API checks succeeded after correcting a harness egress rule.

[All live artifacts](../../results/validation/phase6-5/live/). Initial setup and network harness failures are retained. A simulated destructive boundary was intercepted; no source deletion was executed for that test.

## Cleanup

[Cleanup evidence](../../results/validation/phase6-5/live/cleanup.json) records removal of only the owned cluster, restoration of inotify max_user_instances to 128 and preservation of the pre-existing kind cluster. Private review state and generated credentials were removed. Historical evidence was retained.

## Changed files and design choices

[Exact phase delta](../../results/validation/phase6-5/phase65-changed-files.json) compares the pre-review inventory, not the much older Git HEAD. Six schemas enforce already-required input constraints while retaining valid legacy forms. The recovery guard rejects impossible future targets before any command; complete WAL validation remains unresolved. Documentation changes correct factual inconsistencies, and new review reports expose remaining risks. The new live harness is a bounded review tool, not a product lifecycle feature.
