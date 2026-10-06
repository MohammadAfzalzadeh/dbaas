# API security

## Authentication

All `/api/` routes require `Authorization: Bearer <token>`. This includes deploy and values preview and automatically covers future delete/backup/recovery paths. No such destructive HTTP endpoints exist today. Unknown protected paths return 401 before routing when unauthorized; authentication does not implement those operations.

The operator supplies DBAAS_API_TOKEN through environment or the Deployment's dbaas-api-auth Secret. A missing/short token disables API operations with **503**. Missing/incorrect Bearer credentials return **401** and WWW-Authenticate. Constant-time comparison is used. Use a cryptographically random token of at least 32 characters. The server does not load .env automatically; `.env.example` documents variables only.

The browser accepts the token through a password input. It is sent only in the Authorization header, never a URL, cookie, hardcoded script, localStorage or sessionStorage. It remains in page memory until cleared/reloaded; successful submission clears password fields. Errors are displayed as text. The form uses external Secret mode by default; inline controls apply only to explicitly enabled development mode.

`/` and static assets remain public so the login-capable form can load. `/healthz` remains public for Kubernetes probes and contains no configuration. OpenAPI/docs routes are disabled. CORS preflight is unauthenticated; actual API operations still authenticate. Responses that reach the downstream handler receive no-store/nosniff headers; early authentication failures currently return before those headers are added.

## Authorization and transport

DBAAS_ALLOWED_NAMESPACES is a comma-separated operator allowlist, default dbaas. Authenticated requests outside it receive **403**. Kubernetes Roles/Bindings must independently authorize the backend in each namespace. This shared token represents a trusted platform operator: it has no per-user or per-release ownership model. It is not multi-tenant authorization.

Same-origin requests work without CORS configuration. DBAAS_ALLOWED_ORIGINS can name exact additional origins; wildcard is rejected at startup and credentialed CORS is disabled. For development, list the exact local frontend origin. CORS is a browser policy, not authentication.

Terminate TLS through an operator-configured trusted ingress or reverse proxy before network exposure. This phase does not install a certificate issuer or enforce all cluster transport encryption. Anyone holding the token can act within allowed namespaces; token theft is an operator-level compromise.

## Errors, subprocesses and inputs

Validation errors omit submitted values; unhandled errors omit stack traces. Helm stdout/stderr and generated manifests are neither logged nor returned. Logs retain operation type, outcome and return code. Preview recursively redacts password/pass, secret/key/token and endpoint fields. Namespace/release/Secret names reject path traversal; numeric inputs have bounds; S3 URLs reject embedded credentials and queries. Administrative usernames are restricted because replication HBA is generated as text; PgCat database/user strings are serialized and retain supported PostgreSQL punctuation.

Commands use argument arrays without shell=True, return checks and timeouts (660 seconds for deployment/recovery commands, 30 seconds for chart-default inspection). Timeouts do not imply rollback: inspect Helm/Kubernetes state before retrying. Partial deployment reports completed releases without exposing subprocess output. Phase 1 private temporary files remain in use.

## Rotation

Replace the token in dbaas-api-auth and restart the backend to refresh environment values. Notify operators out of band; no token was generated or distributed by this change. Short overlap/multiple tokens, user identities, audit attribution, rate limits and per-release authorization are **Future Work**. Operator shell recovery uses kubeconfig/Kubernetes authorization, not this HTTP token, and still requires --execute.
