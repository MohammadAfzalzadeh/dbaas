# Split-brain analysis

Review date: 2026-10-04. Verdict: reasonable coordination mechanisms, incomplete fencing evidence; no split-brain guarantee.

## Implemented mechanisms

Patroni coordinates leadership through Kubernetes DCS. PostgreSQL role labels drive primary/replica Services; Services route traffic but do not fence an old primary. StatefulSets preserve identity and PDBs constrain voluntary eviction; neither elects a database leader. Current lab settings and source inspection are in [review evidence](../../results/validation/phase6-5/live/postgres-settings.json).

The installed Patroni defaults are TTL 30 seconds, loop wait 10 seconds and retry timeout 10 seconds. The dynamic configuration does not enable synchronous mode or failsafe mode. Installed source defaults maximum_lag_on_failover to 1,048,576 bytes and replication slots to enabled. Missing keys in the captured private-default dictionary are not proof that effective defaults are absent. See [default-source excerpts](../../results/validation/phase6-5/patroni-defaults.txt).

## Failure assumptions

| Failure | Expected mechanism | Evidence boundary |
|---|---|---|
| Primary process/pod stops | Replica eligibility and DCS leadership acquisition | Prior node-loss experiments observed promotion and SQL recovery |
| Primary cannot refresh DCS | Patroni normally demotes before leadership expires | No exhaustive asymmetric-partition test in this review |
| API server unavailable | Leadership refresh and promotion depend on DCS access | No multi-control-plane outage availability claim |
| PostgreSQL runs while Patroni is paused | Timely demotion can be compromised | No verified hardware watchdog or external STONITH fencing |
| Old primary returns | Follow new timeline, rewind or reinitialize | Three clean recoveries; one historical convergence failure remains unresolved |
| Client retains connection to former primary | Service updates do not terminate every established session | Routing alone cannot prove absence of dual writable primaries |

The Kubernetes control plane must provide consistent leadership state. Patroni must receive CPU time and be able to stop/demote PostgreSQL within the expected lease window. A host pause, asymmetric connectivity, stalled process or failed shutdown can violate assumptions that ordinary pod-kill tests do not cover. Label-based NetworkPolicy is a traffic boundary, not an independent fencing authority.

## Data-loss model

SQL reported synchronous_commit=on but synchronous_standby_names empty: commit waits for local durability, not a remote synchronous replica. Acknowledged primary WAL that never reached the promoted replica can be lost. Lag eligibility uses sampled state and does not establish a guaranteed byte or time RPO. Neither archive_timeout=60 nor a successful base backup guarantees a complete recoverable WAL chain.

Replication slots preserve needed WAL while storage lasts; max_slot_wal_keep_size=-1 permits unbounded slot retention and disk exhaustion. wal_keep_size=128 MB is not a recovery guarantee. Checksums and use_pg_rewind support divergent-member repair when prerequisites hold; rewind is not an independent backup.

## Permanent storage loss

Pod replacement on the same surviving PVC, temporary node loss, returning-node convergence and permanent worker/disk loss are distinct. Local-path PVCs do not follow a dead worker. If a healthy replica survives, an operator must replace failed storage and reseed a member. If every usable database copy is lost, recovery depends on a valid base backup and continuous WAL on surviving independent storage. The lab's MinIO shares the host failure domain. Independent off-site restore remains NOT VALIDATED.

## Future work

Exercise asymmetric API/database partitions, Patroni process pauses, failed demotion and independent host/storage loss. Observe writability on both old and new primaries, not just labels. Evaluate watchdog/fencing and synchronous policy against explicitly chosen durability and availability objectives before production.

Reference behavior: [Patroni replication modes](https://patroni.readthedocs.io/en/rel_3_3/replication_modes.html), [watchdog](https://patroni.readthedocs.io/en/rel_3_3/watchdog.html), [DCS failsafe](https://patroni.readthedocs.io/en/rel_3_3/dcs_failsafe_mode.html). These describe mechanisms; installed source and observed settings establish this repository's configuration.
