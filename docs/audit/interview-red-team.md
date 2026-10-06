# Interview red-team

Review date: 2026-10-04. Answers are bounded by the [independent review](final-independent-review.md) and [claims audit](final-claims-audit.md).

## 1. Does this guarantee zero RPO?

- **Weak answer:** No acknowledged data can ever be lost.
- **Repository support:** Finite acknowledged-ID retention; async replication.
- **Defensible answer:** Only the observed acknowledged set survived. Unreplicated committed WAL can be lost.

## 2. What is the RTO?

- **Weak answer:** About 25 seconds.
- **Repository support:** Separate promotion, SQL and client milestones in one lab.
- **Defensible answer:** We measured bounded events; no agreed objective or guaranteed recovery time exists.

## 3. What makes a write acknowledged?

- **Weak answer:** The INSERT was sent.
- **Repository support:** Client records success after commit returns.
- **Defensible answer:** The client received commit acknowledgement, then recorded a unique ID.

## 4. Can a failed transaction have committed?

- **Weak answer:** Failure means rollback.
- **Repository support:** Connection loss can make commit outcome unknown.
- **Defensible answer:** Yes. We preserve failures and do not blindly replay them.

## 5. Why is a StatefulSet insufficient?

- **Weak answer:** It provides PostgreSQL HA.
- **Repository support:** Stable identities/PVCs; Patroni handles leadership.
- **Defensible answer:** It manages pods and storage identities, not database election or history.

## 6. Can split brain happen?

- **Weak answer:** Patroni makes it impossible.
- **Repository support:** DCS coordination; incomplete pause/partition/fencing tests.
- **Defensible answer:** Safety depends on consistent DCS and timely demotion. We have not proven every partition case.

## 7. What if the API server disappears?

- **Weak answer:** The database is independent of Kubernetes.
- **Repository support:** Patroni leadership refresh depends on Kubernetes DCS.
- **Defensible answer:** Existing behavior depends on lease/demotion rules; this lab does not prove API-outage availability.

## 8. Does a Service fence the old primary?

- **Weak answer:** Only the selected primary can write.
- **Repository support:** Service selectors route new connections.
- **Defensible answer:** Existing connections and direct pod paths are separate; routing is not fencing.

## 9. What does synchronous_commit=on mean here?

- **Weak answer:** Replicas confirmed every commit.
- **Repository support:** Empty synchronous_standby_names.
- **Defensible answer:** It waits for local commit durability, without a configured synchronous standby wait.

## 10. What does maximum_lag_on_failover bound?

- **Weak answer:** Data loss can never exceed 1 MiB.
- **Repository support:** Default 1 MiB eligibility threshold and sampled state.
- **Defensible answer:** It screens candidates, but sampling and later primary WAL prevent that absolute guarantee.

## 11. Do slots prevent all WAL loss?

- **Weak answer:** Slots make recovery certain.
- **Repository support:** Slots retain required WAL; unlimited slot retention configured.
- **Defensible answer:** They help replication but can fill disk and do not preserve a destroyed primary disk.

## 12. Why pg_rewind?

- **Weak answer:** It recovers any broken node.
- **Repository support:** Checksums and use_pg_rewind configured.
- **Defensible answer:** It can repair divergent history when prerequisites hold; reinitialization may still be required.

## 13. Was the historical replica failure fixed?

- **Weak answer:** Three passing reruns prove it.
- **Repository support:** One unresolved failure, three later clean recoveries.
- **Defensible answer:** It remains unresolved and was not reproduced in those reruns.

## 14. What if a worker and disk are permanently lost?

- **Weak answer:** Kubernetes moves the PVC.
- **Repository support:** Node-local storage.
- **Defensible answer:** Replace storage and reseed from a surviving copy, or restore a verified backup chain.

## 15. Is MinIO off-site backup?

- **Weak answer:** It uses S3 so yes.
- **Repository support:** MinIO shares the lab host.
- **Defensible answer:** S3 compatibility describes an API, not independent disaster resilience.

## 16. Does successful backup prove restore?

- **Weak answer:** WAL-G exited zero.
- **Repository support:** Catalog/object evidence plus separate row-checked restore.
- **Defensible answer:** Only an actual restore with data assertions supports that target and chain.

## 17. Can destructive PITR always fail safely?

- **Weak answer:** All preconditions are checked.
- **Repository support:** Future/ownership guards; missing complete WAL coverage proof.
- **Defensible answer:** No. Prefer isolated rehearsal; past unreachable targets can pass metadata preflight.

## 18. Why separate clone archives?

- **Weak answer:** A writable clone can keep following source WAL.
- **Repository support:** Post-bootstrap source archive access disabled; restart tests.
- **Defensible answer:** Source and promoted-clone timelines diverge; continuing source archive recovery risks incorrect history.

## 19. Is clone restart proof of disk-loss recovery?

- **Weak answer:** Yes, it survived deletion.
- **Repository support:** New pod reused its clone PVC.
- **Defensible answer:** It proves restart durability on surviving storage, not recovery from permanent disk loss.

## 20. Does PgCat improve throughput?

- **Weak answer:** Pooling always makes it faster.
- **Repository support:** Direct comparison was faster at the reported mixed point.
- **Defensible answer:** Pooling serves connection management; measured performance depends on workload and routing.

## 21. Is 6.40% the average backup cost?

- **Weak answer:** That is the backup overhead.
- **Repository support:** One 15-second pair with shared-host interference.
- **Defensible answer:** It is the arithmetic difference of one short paired observation.

## 22. Are direct and proxy benchmarks equivalent?

- **Weak answer:** Only the proxy differs.
- **Repository support:** Primary direct path versus role-routed proxy; no catch-up barrier.
- **Defensible answer:** They do not isolate proxy overhead; repeated controlled equivalent-backend tests are future work.

## 23. Is create idempotent?

- **Weak answer:** Same input is a no-op.
- **Repository support:** Serial calls trigger Helm upgrades.
- **Defensible answer:** The API repeats orchestration; it has no no-op/idempotency-key guarantee.

## 24. What happens with concurrent same-name creates?

- **Weak answer:** Helm makes the whole request atomic.
- **Repository support:** One success and one generic failure in the live pair.
- **Defensible answer:** No API lock coordinates all component releases; conflicting requests remain an important risk.

## 25. What if PgCat fails after PostgreSQL deploys?

- **Weak answer:** Everything rolls back.
- **Repository support:** HTTP 400 lists completed releases; partial state remains.
- **Defensible answer:** Operators inspect partial state and retry/correct it; the bounded retry succeeded.

## 26. Are two releases tenant isolated?

- **Weak answer:** Distinct names prove tenant security.
- **Repository support:** A/B markers/selectors separate; shared operator privileges.
- **Defensible answer:** Resource/routing isolation was tested, while identity and adversarial tenant authorization are absent.

## 27. Can an authorized operator reference another Secret?

- **Weak answer:** The namespace allowlist prevents that.
- **Repository support:** References may name Secrets in an allowed namespace.
- **Defensible answer:** The token represents a trusted operator; there is no per-release Secret ownership authorization.

## 28. Is Patroni REST protected by authentication?

- **Weak answer:** It is internal, so secure.
- **Repository support:** No configured REST auth; policy limits reachable peers.
- **Defensible answer:** Permitted peers are trusted and can reach a sensitive management surface.

## 29. Does Gitleaks prove no secrets exist?

- **Weak answer:** The scan passed, so yes.
- **Repository support:** Default rules miss known low-entropy historical values.
- **Defensible answer:** We need history review and revocation of any real old credentials in addition to scanning.

## 30. Can I reproduce from current HEAD?

- **Weak answer:** Everything is committed.
- **Repository support:** Clean candidate includes untracked work; HEAD has 77 entries.
- **Defensible answer:** The working candidate reproduced, but publication must include the intended complete file set.

## 31. Are the builds reproducible bit for bit?

- **Weak answer:** Pinned top-level versions guarantee it.
- **Repository support:** Cached builds, mutable tags/packages, incomplete dependency locks.
- **Defensible answer:** Buildability was reproduced; artifact identity was not established.

## 32. Do denied probes prove policy correctness?

- **Weak answer:** Four failures prove total isolation.
- **Repository support:** Four timed-out paths plus positive SQL/DNS/API under explicit Calico policies.
- **Defensible answer:** They prove those source/destination paths in that profile; wider policy correctness needs more tests.

## 33. Does changing a password revoke sessions?

- **Weak answer:** All old sessions disappear.
- **Repository support:** Held sessions continued; new connections tested.
- **Defensible answer:** Login rotation and existing-session revocation are separate operations.

## 34. Is observability complete?

- **Weak answer:** Grafana dashboards mean full coverage.
- **Repository support:** Seven broken scrape targets; notification delivery unvalidated.
- **Defensible answer:** Available component dashboards work within recorded gaps; complete alert delivery is not established.

## 35. Why publish failed experiments?

- **Weak answer:** They weaken the portfolio.
- **Repository support:** Failures distinguish known outcomes from assumptions.
- **Defensible answer:** Keeping them makes limits and follow-up work auditable and prevents false reliability claims.
