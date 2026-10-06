# Isolated restore and controlled cutover

The operator tools create a new Patroni release and new PVCs. They do not change the source StatefulSet, delete source volumes or switch application endpoints. Execution still requires `--execute`; dry run renders and checks names/backup metadata. See the Phase 5 evidence index for the live validation scope.

```sh
python3 scripts/isolated-restore.py --namespace dbaas \
  --source-release source-patroni --target-release recovery-patroni \
  --recovery-time '2026-01-01 12:00:00'
# Review the plan, then repeat with --execute.
```

Use an actual UTC target supported by your backup/WAL history. Preflight rejects existing target Helm resources/PVC names. The source must use external Secrets. The target initially references the same credential/config Secrets in the same namespace, so it belongs to the same trusted-operator boundary. Prepare independent target Secrets before production use or credential rotation. When source NetworkPolicies are enabled, provide an explicitly reviewed `--network-values` file; source selectors cannot safely be copied blindly. Network separation must be established by the operator.

The target disables WAL archiving and backup CronJobs to prevent a writable clone from putting a new timeline into the source prefix. WAL fetch is available during bootstrap; the helper then disables subsequent source archive reads. This is a validation target, not a continuously protected replacement service. Before ongoing writes/cutover, supply an independent archive destination, enable archiving/backups through reviewed Helm values, restart as required, and prove a new backup/restore.

## Planned cutover procedure

1. Identify the required recovery point and application consistency boundary. Freeze source writes when a lossless planned migration is required; restoring an earlier timestamp intentionally excludes later commits.
2. Record source release/PVC identities, backup identifier, target UTC, expected row counts/checksums and acknowledged transaction IDs. Protect a copy outside the source failure domain.
3. Restore under a unique release and volume set. Require exactly one leader, healthy replicas, intended Service endpoints and explicit target-time data assertions.
4. Establish independent credentials, archive prefix, monitoring and access policy. Exercise writes and a backup on the target.
5. Obtain the application owner's cutover decision. Switch the application endpoint using its supported configuration/reconnect mechanism. No tool here performs DNS or production cutover automatically.
6. Monitor application errors, replication, archive progression and backup completion. Retain the old source isolated from writes for the agreed rollback window.
7. Rollback after target writes requires a data reconciliation decision; switching the endpoint back alone can discard new commits. Record the authoritative writer and prevent simultaneous writes to both clusters.

Source-controlled sequence: [restore-cutover.mmd](../diagrams/restore-cutover.mmd). Rendered version: [restore-cutover.svg](../images/architecture/restore-cutover.svg).

## External recovery

For a fresh cluster without access to the source Kubernetes API, use `scripts/offsite-restore.py` with an explicit kubeconfig, new target release, existing PostgreSQL/WAL-G Secrets, selected backup and UTC target. Restore readiness alone does not establish correctness: compare the saved dataset and verify writability. External-target results remain NOT VALIDATED unless the evidence index records an actual external experiment.

## Clone archive isolation after promotion

The first Phase 5 clone failed to restart after worker loss while reading the source archive. A timeline collision is suspected. The helper now disables both ongoing source archive reads and writes. Custom bootstrap still uses WAL-G to reach the target time. Before reporting readiness, the helper checks running PostgreSQL settings and, if needed, restarts only the new clone through Patroni to leave bootstrap recovery settings behind. This adds time to restore readiness. The continuation clone passed both graceful and abrupt pod replacement; it does not establish permanent disk-loss recovery or every crash scenario. Configure an independent archive prefix and validate it before any cutover. See [Patroni custom bootstrap behavior](https://patroni.readthedocs.io/en/latest/replica_bootstrap.html).
