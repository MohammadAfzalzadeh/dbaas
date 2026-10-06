# Security model

This is a trusted-operator platform with a minimal shared-token boundary, not a production multi-tenant DBaaS.

## Trust boundaries

1. Browser/client → FastAPI: Bearer authentication, namespace allowlist, input validation, sanitized errors. TLS is an operator prerequisite.
2. FastAPI → Helm/Kubernetes: the backend ServiceAccount's namespace Role is the authority. The shared token permits operations within that scope, including upgrades; release ownership is not checked per user.
3. Kubernetes → database/proxy/backup containers: externally managed Secrets carry runtime credentials. Anyone allowed to read Secrets, exec into pods, or control these containers/nodes is trusted with those credentials.
4. PostgreSQL/WAL-G → object storage: backup credentials must be provisioned consistently; local backup/WAL and isolated restore have lab evidence; arbitrary WAL-chain completeness and independent off-site recovery remain unverified.
5. Source/build → images: direct versions, npm integrity lock, versioned downloads and source checksums reduce drift. Mutable tags, apt repositories, Python transitive resolution and unsigned build artifacts remain supply-chain boundaries.

## Present protections

API fail-closed authentication; operator namespace allowlist; no plaintext credential defaults or credential-bearing ConfigMaps; external Secret references; redacted preview/error paths; private generated files; shell-free Python commands with timeouts; JS dependency lock; Gitleaks CI configuration. These changes preserve the Phase 1 routing/backup/recovery guards.

## Remaining risks

No tenant identity/quotas/ownership, complete TLS policy, rate limiting, durable operation/audit store or credential-rotation controller. Release NetworkPolicy scaffolds have enforcing-CNI lab evidence, but are not a tenant authorization boundary. Kubernetes Secret data is not automatically encrypted simply because it is a Secret. Inline development mode leaves sensitive values in Helm history. Old resources and Git history may retain earlier credentials. Default public MinIO metrics and Patroni control/metrics access still need network policy. Container UID/securityContext changes require storage/shared-volume testing and are deferred.

The raw kuberResources examples now reference external Secrets, but their pre-existing deployment defects are still documented in the audit. Do not treat their sanitization as end-to-end validation. The Phase 2 security changes did not include live drills. Later phases exercised scoped backup/restore and network-policy cases; no comprehensive security assessment, image vulnerability scan or production certification is claimed.

## Git history and scanning

`.gitignore`/build ignores exclude local environment/Secret files and dependency caches without excluding examples or the npm lockfile. Existing tracked credentials were removed from the working tree; this does not erase history or Helm records.

GitLab CI runs Gitleaks v8.24.3 default rules against both files and complete history with redacted output. It has no blanket source/test allowlist. Historical findings intentionally remain actionable. A checksum-verified Gitleaks v8.24.3 binary in /tmp scanned the working tree and 148 reachable local commits with no findings under its default rules. The CI job itself has not run. This result does not detect or invalidate the separately identified low-entropy historical passwords. Operator review is still required for low-entropy passwords that generic scanners may miss. Rotate affected deployed credentials first, then coordinate history remediation with repository owners. This task did not rewrite history or rotate live credentials.
