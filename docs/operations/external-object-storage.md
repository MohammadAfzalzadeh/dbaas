# Provider-neutral S3-compatible backup storage

Local development uses WAL-G → single MinIO/local volume. That storage shares the lab's physical failure domain. The external configuration path uses WAL-G → an operator-supplied S3-compatible endpoint; the project does not select a provider or require public-cloud credentials in CI.

`walg.existingSecret` remains the chart/API contract for the complete `.walg.env` file. Existing deployments remain compatible. `scripts/object-storage.py` prepares that Secret using two existing Kubernetes Secrets, keeping credentials out of command arguments, generated repository files and output:

- Object-storage input Secret: `access-key`, `secret-key`.
- PostgreSQL input Secret: `superuser-username`, `superuser-password`.
- Output Secret: `.walg.env` with quoted dotenv values (not JSON).

```sh
python3 scripts/object-storage.py --namespace dbaas \
  --credential-secret external-s3-credentials \
  --postgres-secret source-postgres-credentials \
  --output-secret source-external-walg \
  --endpoint https://s3.example.com --bucket YOUR_BUCKET \
  --region YOUR_REGION --path-style
# Review the non-secret settings; add --apply to write the output Secret.
```

Use `--no-path-style` for a provider that requires virtual-host addressing. TLS is required by default. `--allow-http-development` permits a local HTTP endpoint explicitly; it does not disable certificate validation for HTTPS. Certificate trust must be configured correctly in the image/environment. Endpoint URLs containing credentials or query strings are rejected. The tool does not create the bucket, grant IAM permissions or prove recoverability.

Configure `existingSecrets.walg` in the API request, or `walg.existingSecret` in Helm. Disable local MinIO provisioning when using external storage. The full WAL-G config Secret is authoritative; legacy inline S3 API fields are development-only and do not override an external config Secret.

## Integration drill without source-cluster access

1. Configure the source to archive and back up to the external target.
2. Create A, take the official CronJob-derived backup, record target T, create B and verify archived WAL.
3. Export only expected data/backup metadata to evidence. Prepare independent credential Secrets securely in a fresh disposable cluster.
4. Run `scripts/offsite-restore.py --kubeconfig PRIVATE_PATH --namespace dbaas --target-release external-restore --postgres-secret RESTORE_PG_SECRET --walg-secret RESTORE_WALG_SECRET --backup-name SELECTED_BASE_BACKUP --recovery-time 'UTC_TIMESTAMP'` and review its dry run; then add `--execute`.
5. Verify A present/B absent, write C, validate roles, then clean up only the owned lab.

Without an actual external target, this is STATICALLY VALIDATED tooling and NOT VALIDATED off-site recovery. A local second bucket or container is not evidence of an independent failure domain. Retention, object lock, IAM restrictions, encryption/key recovery, egress cost and off-site restore policy remain operator responsibilities.
