# Secret inventory

Inventory date: 2026-10-03. Scope: tracked source plus uncommitted Phase 1/2 files, chart-generated configuration and the known runtime paths. No real values are reproduced. Historical credentials were not tested for validity; presume exposure if any were deployed. This is a source inventory, not a scan of running clusters or user home credentials. Gitleaks additionally scanned 148 reachable local commits with no default-rule findings; low-entropy historical passwords remain known inventory findings despite that result.

| Surface / fields | Classification | Phase 2 disposition |
|---|---|---|
| Both Patroni values.yaml/values-base.yaml: SUPERUSER_PASSWORD, REPLICATION_PASSWORD | UNSAFE_TRACKED_SECRET (baseline) | Defaults cleared; external postgres Secret, inline only by opt-in |
| Both Patroni values files: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY | UNSAFE_TRACKED_SECRET (baseline) | Defaults cleared; external WAL-G config Secret |
| Both PgCat defaults and legacy application pgcat-values.yaml: admin/pool PASSWORD, pgAdmin pass | UNSAFE_TRACKED_SECRET (baseline) | Defaults cleared; existing config/admin Secrets |
| Both MinIO defaults: rootPassword/rootPasword, backupPassword | UNSAFE_TRACKED_SECRET (baseline) | Defaults cleared; existing credentials Secret |
| Raw kuberResources: PostgreSQL/replication environment, WAL-G Secret literals, PgCat ConfigMap, MinIO ConfigMap/environment | UNSAFE_TRACKED_SECRET (baseline) | Credential literals removed; operator-managed Secret refs; scripts contain variable names only |
| Former PgCat Jinja pgAdmin fallback password | UNSAFE_TRACKED_SECRET (baseline) | Removed; external Secret by default, explicit development input only |
| Chart/example usernames, Service DNS names and example.invalid email | SAFE_EXAMPLE | Not credentials by themselves; select actual identities through Secrets |
| Phase 1/2 tests: synthetic passwords/tokens and fake WAL-G credentials | TEST_ONLY | Clearly synthetic; never deployed; tests remain in scanner scope |
| DBAAS_API_TOKEN / dbaas-api-auth token | RUNTIME_SECRET | Environment/Secret; no committed value, no automatic fallback |
| Operator existing PostgreSQL, replication, PgCat, pgAdmin, MinIO and AWS credentials | RUNTIME_SECRET | Namespace Secrets; mounted or secretKeyRef; not copied into normal API Helm values |
| External pgcat.yaml and .walg.env, credential-bearing endpoints/connection strings | RUNTIME_SECRET | Treat entire files as sensitive; protect PG/S3 password copies required by consumers; API forbids endpoint userinfo/query |
| Development inline rendered Kubernetes Secrets / Helm release history | GENERATED_SECRET | Explicit opt-in; persists in Helm storage until operator cleanup |
| API private values and recovery saved values | GENERATED_SECRET | Unique private directories, 0600, cleanup on completion/error; normal API external mode contains only references |
| Patroni generated patroni.yml; watcher generated pgcat.toml; MinIO mc alias configuration | GENERATED_SECRET | Private runtime files; never source-controlled; trusted pod/node boundary |
| .env.example / values.example.yaml / pgcat-config.example.yaml | SAFE_EXAMPLE | Empty credential slots or names only; populated local variants must remain ignored |
| Historical API preview, browser output, Helm debug output and old temp files | GENERATED_SECRET (historical exposure risk) | Current paths sanitized; inspect and remediate any retained historical copies privately |

**Required if previously used:** rotate PostgreSQL superuser/replication and PgCat user/admin passwords, pgAdmin login, MinIO root/backup credentials and any reused AWS access keys. If a token or connection string was ever committed, revoke/rotate it too. No assertion is made that example credentials were live. Removing files does not revoke credentials, erase Git history, clear old ConfigMaps or purge Helm release history.
