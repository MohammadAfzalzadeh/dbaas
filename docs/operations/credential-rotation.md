# Credential rotation rehearsal

Changing a Kubernetes Secret does not automatically change PostgreSQL roles or reload every consumer. Use the Phase 5 `rotation.json` artifact for the exact rehearsed scope. All examples below are procedures, not a claim that every credential class has been exercised.

| Credential | Required coordination | Validation boundary |
|---|---|---|
| Application PostgreSQL role | Change the SQL role and client Secret; invalidate old new-session authentication; existing sessions can remain authenticated | Disposable role rehearsal records old/new login outcomes. |
| PgCat configured user | Align the database password and pgcat.yaml Secret; wait for projected-file update and PgCat autoreload, then verify each proxy | Continuation validated reload without proxy restart; existing sessions remained usable. |
| Patroni replication user | Coordinate SQL password, Secret-backed environment and member restarts; start with a replica, check streaming, then controlled primary transition | NOT VALIDATED; do not rotate blindly on a running cluster. |
| PostgreSQL superuser / WAL-G | SQL password, Patroni environment, WAL-G dotenv and operational clients must agree | NOT VALIDATED; a stale WAL-G PGPASSWORD can break base backups. |
| MinIO / external object store | Provision a second least-privilege credential, update WAL-G Secret, prove archive/backup/restore, then revoke old credentials | NOT VALIDATED. Existing-user MinIO hook does not rotate passwords. |
| API Bearer token | Secret-backed environment requires a workload restart; coordinate operator clients | NOT VALIDATED rotation. Shared token remains a coarse trust boundary. |

Never put passwords in shell command arguments, Helm values/history, screenshots or evidence. The rehearsal passes SQL password parameters via stdin inside the trusted disposable client. Evidence records outcomes and Secret names, not values. Two-role overlap is preferable where clients cannot switch atomically. Record connection resets and reconnect behavior instead of assuming uninterrupted sessions.

## Rehearsal

Run the `rotation` stage of `scripts/resilience/lab.py` only with its private state directory identifying the task-owned lab. The application role is separate from the operator and replication users. Old-password rejection is checked on new direct and PgCat connections. Secret projection timing and explicit rolling restart must be considered separately from SQL password changes.

For production, rehearse each credential class with your authentication mode, client pooling, Secret delivery mechanism and rollback plan. Password changes alone do not revoke already authenticated sessions; terminating those sessions is a separate, potentially disruptive operation.

## Continuation reload rehearsal

`scripts/resilience/rotation-reload.py` uses a disposable role and identity-checked lab. It tests each proxy Pod IP, verifies both new-password acceptance and old-password rejection, and holds direct/Service sessions without reconnecting. Observed propagation was 73.658 seconds, including Secret projection and PgCat’s 15-second polling. Updating the SQL role first creates a transition window; use overlapping roles if an application cannot tolerate that window. See the [continuation report](../audit/phase5-continuation-report.md).
