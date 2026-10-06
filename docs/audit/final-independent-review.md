# Executive Verdict

**GO WITH CAVEATS for a portfolio research prototype; NO-GO for production deployment.** Independent checks support the core implementation and many bounded lab observations. They do not establish guaranteed RPO/RTO, tenant security, split-brain immunity or representative performance. Publication conditions are in [publication readiness](publication-readiness.md).

Review date: 2026-10-04. Evidence: [Phase 6.5 artifacts](../../results/validation/phase6-5/). This review tested the complete working-tree candidate without committing or pushing it.

# Claims Audit

[Claim-by-claim review](final-claims-audit.md) extracts exact major claims from the README, executive and engineering reports, LinkedIn draft, carousel, resume and interview documents. Existing reports were treated as assertions, then checked against code and raw artifacts. Confirmed inconsistencies were corrected; successful historical observations retain their original scope.

# Reproducibility

A clean candidate copy excluded Git metadata and generated state. Fresh Python dependency installation and npm ci succeeded without developer package configuration. Tests and all seven image builds succeeded. The static/link validators require Git metadata: the archive-only attempt failed; initializing an empty local Git directory made discovery work. No commit was created. BuildKit cache was allowed, so this is not a cold-cache or byte-for-byte reproducibility result.

Current HEAD has only 77 tree entries; much of the candidate is untracked. A clean candidate copy includes those intended files and cannot prove that cloning current HEAD reproduces the project. [Path audit](../../results/validation/phase6-5/path-audit.json) classifies 4,933 occurrences including historical artifacts and legitimate temporary paths. Runtime defaults use repository-relative paths; lab kubeconfig paths and hardcoded owned-cluster assumptions remain explicit operator context. The legacy init.bash must not be run against an unrelated cluster.

# Kubernetes Review

All six active charts were linted and rendered under 90 adversarial combinations, plus six same-namespace name-collision comparisons. New schemas reject negative replicas, invalid ports, malformed Secret names and required null sections. Profiles that set irrelevant chart keys do not constitute meaningful validation tests for those keys. Scale-to-zero remains accepted where previously supported.

Fresh same-namespace A/B deployments used distinct StatefulSets, PVCs, Services, Secrets and Patroni identities. Ten SQL connections per proxy returned only its own marker. The monitoring CRD was absent in this lab: monitoring isolation was reviewed from rendered selectors, not live scrape results. Four denied network paths timed out under Calico; normal SQL, DNS resolution and API access worked. These were explicit review policies, not proof that arbitrary user policy values are safe. The first review-policy attempt omitted required PostgreSQL-to-proxy egress; its failed log is retained and the harness corrected.

# PostgreSQL Review

Current SQL settings show asynchronous replication semantics: synchronous_commit=on with empty synchronous_standby_names. Commit-confirmed WAL absent from a promoted replica can be lost. Slot retention, checksums and rewind improve recovery options but do not guarantee durability or bound disk consumption. See [split-brain and storage analysis](split-brain-analysis.md) and captured effective settings. The independent A/B lab used one PostgreSQL member per release; historical three-member failure evidence was inspected, not silently repeated as a new HA test.

# DBaaS Control Plane Review

Two different releases provisioned concurrently with isolated private temporary values and correct response/resource mapping. Serial duplicate requests performed Helm upgrades. Simultaneous identical releases returned one success and one generic command failure. The sanitized response does not establish the exact Helm internal failure reason. There is no API provisioning lock, durable operation record or idempotency key; component-level Helm behavior cannot guarantee atomic multi-release orchestration.

An intentionally missing PgCat Secret left MinIO and PostgreSQL deployed, returned HTTP 400 with both completed release names, and left a failed PgCat release. PostgreSQL remained queryable. Concurrent cluster B provisioning succeeded. Correcting the input and retrying completed successfully. This proves reported partial completion, not rollback. Delete/nonexistent lifecycle operations are not implemented API contracts.

# Backup/PITR Review

Official CronJob-derived Jobs succeeded before and after four faults: missing primary target, unreachable endpoint, wrong object credentials and unavailable MinIO. Each fault produced a Failed Job with no new backup catalog entry; captured output contained no known generated credential. Tests used bounded retries/deadlines and remote command timeouts. Cluster B's catalog and marker remained intact.

Invalid date, pre-backup date and future target were rejected in live dry runs. Simulated command runners additionally checked absent credentials, empty wrong-prefix catalogs and ownership mismatch. The ownership fixture fails at the StatefulSet selector check; it is not a pure live ambiguous-PVC experiment. A real isolated restore created separate storage and preserved the source.

**Critical residual risk:** base-backup metadata does not prove WAL coverage. Before correction, even a future target could reach the first destructive operation in a simulated in-place restore. Future targets now fail before commands run. A past target after available WAL can still reach that boundary: the review intercepted it without deleting anything. Complete WAL validation before destructive recovery remains future work. Prefer isolated rehearsal; do not describe in-place preflight as proof of recoverability.

# Security Review

API authentication, namespace allowlisting, constrained release names and argument-list subprocess invocation were checked. Per-request values are private; existing Secrets are references. These controls protect a trusted operator workflow, not tenants from one another. An authorized operator can name other Secrets within the allowed namespace. Backend and backup RBAC expose broad namespace Secret/pods-exec capabilities. Patroni REST has no configured authentication; any permitted peer must be trusted accordingly. No destructive exploit was attempted.

The image review inspected seven image histories, users, environment, entrypoints, commands and sizes. Most utility images run as root; Patroni and backend specify non-root users. Kubernetes probes supply health behavior. WAL-G's downloaded amd64 archive lacks checksum verification; other tooling also assumes amd64. Mutable base tags, apt packages and incompletely locked Python transitive dependencies prevent bit-reproducibility claims. No vulnerability-scanner clean bill is claimed. Node 18 and Kubernetes 1.30 are EOL ([Node](https://nodejs.org/en/about/eol), [Kubernetes](https://kubernetes.io/releases/1.30/)). PostgreSQL 16 remains a supported major but the pinned minor is old ([support policy](https://www.postgresql.org/support/versioning/)).

Two initial Gitleaks candidates were public Python image signing fingerprints, not credentials. The exported fingerprint was omitted and triage retained. Default-rule history scanning is insufficient: a separate history review records 37 credential-like candidate locations, some expressions rather than literal secrets. Known low-entropy historical credentials require owner review and revocation if ever used. Values were not published in new evidence.

# Benchmark Review

Independent recalculation matched all 24 raw TPS samples. The backup pair is 1231.639869 versus 1152.865316 TPS, a 6.395908% decrease rounded to 6.40%. It is one short paired observation, not average overhead or an isolated causal cost. Matrix points lack dedicated warm-up, randomized order, repeated samples and a replica catch-up barrier. Direct primary routing and PgCat primary/replica routing are not equivalent backend workloads. Short small-dataset results do not establish capacity, latency percentiles or proxy speedup.

Timing boundaries were inspected: promotion observation, independent SQL probe, persistent-client recovery and member convergence are separate. Restore timings include bootstrap/assertions, backup timing includes Job overhead, and provisioning includes command/deployment latency. The older drain and initial node-loss timers also include setup/blocking observation effects. Credential reload timing begins after database/application changes; it is not whole-operation rotation time. A failed old-password connection was classified by generic connection error, not SQLSTATE, so the narrow observation is connection failure alongside successful new authentication.

# Evidence Quality

Persistent clients record success only after commit returns, with unique per-client transaction IDs and no blind replay of failed operations. Independent recount found 20,624 acknowledged writes and 34 failures; acknowledged IDs were retained in the inspected historical experiment. This supports that finite observed set, not zero RPO. Unknown commit outcomes remain possible for failed requests.

Historical failures are retained. The original replica anomaly remains **UNRESOLVED HISTORICAL FAILURE + NOT REPRODUCED IN SUBSEQUENT CLEAN RUNS**. Review setup/network harness failures are retained separately. Raw historical result hashes are checked against the pre-review inventory. New live credentials stay outside the repository and are removed during lab cleanup.

# Public Repository Quality

Mermaid sources accompany architecture exports. The multi-node diagram incorrectly implied fixed per-proxy database-member routing; source and SVG/PNG now show shared role Services. Existing generated data plots remain tied to raw results. No screenshots or metrics were fabricated.

Keep code, Mermaid, modest SVGs and intentional raw evidence in Git. Large future binary evidence can move to release artifacts or LFS when warranted; current size alone does not justify deleting history. Ignore private kubeconfigs, credentials, dependency directories and transient logs. Review the original research PDF before redistribution. The orphaned rook-config/rook gitlink lacks .gitmodules; it is not an active deployment dependency and was not silently removed.

# Critical Findings

1. In-place recovery can delete source storage before proving a past target's WAL coverage. The future-target guard narrows, but does not solve, this risk.
2. Historical credential remnants require publication review. A default scanner pass cannot establish that past low-entropy credentials are safe.

# Important Findings

- Same-release concurrency lacks a deterministic API-level contract and durable coordination.
- Clean current-HEAD checkout does not contain the complete working candidate.
- Node/Kubernetes baselines need supported-version migration before production.
- Operator trust, plaintext paths, unauthenticated Patroni REST and broad RBAC prevent tenant-security claims.
- Independent failure domains, permanent storage-loss recovery, off-site restore and fencing tests remain incomplete.
- Seven historical scrape targets remain broken; notification delivery is unvalidated.

# Minor Findings

- Required Helm input validation was incomplete; corrected with six schemas and regressions.
- Several older documents lagged later evidence; factual wording synchronized.
- Archive validation requires Git metadata; clean candidate tests document that prerequisite.
- Benchmark and rotation labels need the methodology qualifications above.

# Corrections Made

Added six Helm schemas, seven Python regression test methods, a future-target recovery guard, a bounded independent review harness, reports and raw validation evidence. Updated README, security, monitoring, version, recovery and benchmark documentation only where code/evidence contradicted wording. Updated the report generator's matching methodology paragraph without rewriting old measurement artifacts. Corrected multi-node Mermaid routing and its exports. Schemas preserve valid existing input forms and scale-to-zero; no architecture redesign or new product feature was introduced.

# Remaining Risks

All critical/important findings above remain unless explicitly marked corrected. No guaranteed availability, RPO, RTO, deterministic duplicate provisioning, complete secret-history clearance or comprehensive security audit is claimed. [Validation summary](phase65-validation.md) records exact final checks and cleanup.

# Publication Recommendation

Publish the reviewed candidate as a transparent experimental platform after the file-set and credential-history publication gates are resolved. Use bounded measurements and explain unresolved failures. Keep production deployment out of scope until the documented gates are addressed. See [interview red-team](interview-red-team.md) for defensible answers.
