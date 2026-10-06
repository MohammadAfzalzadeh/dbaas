# Controlled upgrades

PostgreSQL and MinIO default to `OnDelete`; Helm updates the pod template without restarting existing pods. `OrderedReady` remains PostgreSQL's creation ordering, not a primary-aware updater. Operators may opt into RollingUpdate, but ordinal order does not identify the primary and a PDB does not govern that controller's rollout. Do not use automatic RollingUpdate as a failover protocol.

1. Record namespace, release, chart/image revisions, securely saved Helm values, membership, replication lag, PVC UIDs and backup evidence. Test the target image and restore in a disposable environment.
2. Render/diff both values and manifests. Check immutable fields using [migration guide](migration-phase3.md). Apply reviewed Helm changes; confirm OnDelete and unchanged PVC identity.
3. Update one **replica** at a time by deliberately deleting only its pod. Wait for the replacement to be ready, streaming and caught up. Recheck SQL through PgCat and inspect replication before proceeding.
4. Perform a planned Patroni switchover using the existing Patroni interface only after validating the target. Verify the new primary through SQL, Service endpoints and Patroni. This repository does not automate this step.
5. Restart the former primary after it becomes a healthy replica. Stop if any member fails to recover. A one-member deployment requires an outage window.
6. Check final controller revisions, image IDs, roles, actual queries, backups and retained claims. For MinIO's single instance, plan an outage and stop backup jobs before its deliberate restart.

Major PostgreSQL versions need pg_upgrade or logical migration with a separately reviewed plan; changing the image tag is not a major-version upgrade method. PostgreSQL storage is not generally backwards compatible with older binaries. Helm rollback updates manifests; it does not undo data-format changes, deleted PVCs or database writes. With OnDelete it also does not automatically replace existing pods. Preserve backups and stop before any irreversible action if rollback feasibility is unclear.

PgCat Deployments use Kubernetes rolling updates and bounded SQL readiness. Two replicas improve capacity during a restart but established client connections still need reconnect/retry handling. API remains single replica; avoid upgrades during provisioning and serialize operations.
