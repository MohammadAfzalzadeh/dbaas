# Secrets management

Phase 2, 2026-10-03. Existing Kubernetes Secrets are the default. No external secret controller is required. The charts reference Secrets without reading them through Helm `lookup`; rendered default manifests and Helm release values therefore contain names, not password material.

## Secret contract

Create these Secrets **in the release namespace before installation**. Empty `existingSecret` means the release-derived name below, not generated credentials. In API deployments, component release names are `<project>-patroni`, `<project>-pgcat`, and `<project>-minio`.

| Consumer / chart value | Default Secret name | Required keys |
|---|---|---|
| PostgreSQL: `postgres.existingSecret` | `<patroni-release>-postgres-credentials` | `superuser-username`, `superuser-password`, `replication-username`, `replication-password` |
| WAL-G: `walg.existingSecret` | `<patroni-release>-wal-g-credentials` | `.walg.env` |
| PgCat: `existingSecret` | `<pgcat-release>-pgcat-config` | `pgcat.yaml` containing complete watcher configuration |
| pgAdmin: `pgadmin.existingSecret` | `<pgcat-release>-pgadmin` | `pgadmin-password` |
| MinIO: `minio.existingSecret` | `<minio-release>-minio-credentials` | `root-user`, `root-password`, `backup-user`, `backup-password`, `backup-bucket` |
| API Deployment | `dbaas-api-auth` | `token` (unique random value, at least 32 characters) |

The API accepts an `existingSecrets` object with `postgres`, `walg`, `pgcat`, `pgadmin`, and `minio` name fields. It never reads back password values. PostgreSQL env values use secretKeyRef; WAL-G and PgCat mount configuration Secrets; MinIO and pgAdmin use secretKeyRef. Missing Secrets fail workload startup rather than silently using static passwords.

The `.walg.env` extension selects WAL-G dotenv parsing: use one `KEY="value"` assignment per line, **not a JSON object**. Invalid WAL-G configuration can echo its source in upstream error logs; validate formatting before deployment and sanitize captured diagnostics. The WAL-G file needs PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE and AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_ENDPOINT/WALG_S3_PREFIX, plus region/path-style/compression settings appropriate to storage. Use `postgres` as the maintenance database. Its database credentials must match PostgreSQL, and its object-store credentials/bucket must match MinIO. These are required copies for existing consumer formats, not independently generated passwords. Use the existing chart's development template as a format reference without copying historical values.

External `pgcat.yaml` owns database/user/routing configuration. The API's pool fields do not modify an externally managed Secret. Set hosts to `patronimvp-master-<patroni-release>` and `patronimvp-replica-<patroni-release>`. For one PostgreSQL pod, enable PRIMARY_READ and set INCLUDE_REPLICA false. Keep exporter/PGCAT ports aligned with chart pgcatconfig.general settings (9930/5432 defaults). No SQL users/databases are created by the API. See [configuration skeleton](pgcat-config.example.yaml).

Reference-only [Patroni](../../helmCharts/patroni/values.example.yaml), [MinIO](../../helmCharts/minio/values.example.yaml), and [PgCat](../../helmCharts/pgcat/values.example.yaml) examples also work with the application chart family.

## Provisioning and migration

Use an operator-controlled secret store or private files (umask 077). Prefer `kubectl create secret generic ... --from-file=key=/private/path` over password literals in CLI arguments/history. Generate new random credentials locally, never from examples. Do not commit populated files or render Secret YAML to shared logs. Kubernetes Secret storage itself needs encryption at rest and restrictive RBAC managed by the cluster operator.

For an existing installation, first inventory the deployed Secret names and consumers privately. Create **new externally managed Secret names** with compatible current credentials, update references, and verify every consumer. Do not simply reuse a Helm-owned Secret while disabling its template: Helm may delete it during upgrade. Rotate credentials in a coordinated operation after migration. Database role passwords, PgCat auth and WAL-G connections must change together; updating a Secret alone does not rotate PostgreSQL roles. MinIO's hook does not rotate an existing backup user's password. Preserve the Phase 1 immutable-controller migration requirements.

Recovery accepts external Secrets and checks namespaces, keys and live workload references before deletion. It still requires a ready primary and matching backup metadata. It is an Experimental destructive operator workflow, not a recovery API.

## Development-only inline compatibility

Helm `security.allowInlineSecrets=true` permits explicit caller-supplied raw values to render generated Secrets. Password defaults are empty; no static fallback is provided. Existing Secret names take precedence over generating their corresponding Secrets. Root MinIO's legacy `rootPasword` key remains accepted in this mode.

The API additionally requires `DBAAS_ALLOW_INLINE_SECRETS=true` before accepting inline credentials. With no inline credentials, it still emits Secret references. Inline credentials enter private temporary values files and Helm release history; the latter persists beyond file cleanup. Use this only in disposable development environments. Previews redact passwords and other sensitive fields even in development mode.

## Lifecycle and limitations

- API values files use unique private directories, mode 0600 and automatic cleanup. Recovery saved values use the same pattern; both retain credentials in process memory while needed.
- Patroni generates its private YAML with umask 077. Watcher TOML is mode 0600 and atomically replaced; its UID must remain compatible with the PgCat reader. Container root identities were not broadly changed.
- `mc` requires credentials as process arguments for its administrative commands. Shell tracing is disabled and chart initialization diagnostics are sanitized, but privileged observers can inspect process memory/arguments. Treat the Job/node as trusted.
- Vault, Sealed Secrets and External Secrets Operator are **Future Work**, not dependencies introduced here.
- Refer to the [inventory](secret-inventory.md) and [security model](security-model.md) before exposure beyond a trusted environment.
