# Version matrix

Updated 2026-10-03. These are **source/build baselines**, not an inventory of running images or a vulnerability/support certification. The previous floating tags/Git HEAD did not establish a deployed version. Compare actual deployments before rebuilding; do not automatically downgrade or roll these baselines into an existing cluster.

| Component | Version / build input | Purpose | Pinning method | Source/location |
|---|---|---|---|---|
| PostgreSQL | 16.6, Debian bookworm | Database base | Exact minor/base tag | patroni/Dockerfile |
| Patroni | 4.0.4, kubernetes extra | Existing Endpoints DCS, primary/replica labels | Exact pip requirement | patroni/requirements.txt |
| PostgreSQL Python adapter | psycopg2-binary 2.9.10 | Patroni DB access | Exact pip requirement | patroni/requirements.txt |
| Custom Patroni image | dbaas/patroni:2.1.0 | Package local entrypoint and pinned Patroni | Local build release tag; not a published image claim | Both Patroni charts, init.bash |
| PgCat | v1.2.0 | Existing pooler | ghcr.io/postgresml/pgcat:v1.2.0 | Both PgCat charts/raw proxy; manifest verified |
| PgCat watcher | dbaas/pgcat-config-watcher:1.1.1 | Local YAML→TOML adapter | Local build release tag + npm lock | pgcat/Dockerfile, package-lock.json |
| Node | 18.20.8-bookworm-slim | Preserve existing Node major | Exact base tag | pgcat/Dockerfile |
| Watcher dependencies | chokidar 4.0.3; js-yaml 4.3.2; winston 3.17.0; winston-daily-rotate-file 5.0.0 | Existing watch/parse/log behavior | Exact direct versions; lockfile integrity; npm ci | pgcat/package.json, package-lock.json |
| WAL-G | v3.0.7 | Existing archive/backup/restore binary | Versioned amd64 release URL; local image dbaas/wal-g:3.0.7 | wal-g/Dockerfile |
| MinIO | RELEASE.2025-04-22T22-12-26Z | Existing S3-compatible store | Versioned source archive + recorded SHA-256, go.sum, readonly modules; local dbaas/minio tag | minio/Dockerfile, both MinIO charts |
| MinIO client | RELEASE.2025-04-16T18-13-26Z | Existing bucket/user initialization | Versioned source archive + recorded SHA-256; local dbaas/mc tag | minio/mc.Dockerfile |
| Go | 1.24.2-bookworm | MinIO source builds | Exact builder tag matching server toolchain | minio Dockerfiles |
| pgAdmin | 9.3 | Existing administration UI | dpage/pgadmin4:9.3 | Both PgCat templates; manifest verified |
| Python backend base | 3.12.7-slim-bookworm | Preserve Python 3.12 runtime | Exact base tag | application/Dockerfile |
| FastAPI / Uvicorn | 0.115.5 / 0.30.6 | Existing HTTP server | Existing direct pins retained | application/app/requirements.txt |
| Pydantic / Jinja2 / PyYAML | 2.9.2 / 3.1.4 / 6.0.2 | Models/templates/config parsing | Existing direct pins retained | application/app/requirements.txt |
| Recovery tooling | PyYAML 6.0.2 | Parse mounted PgCat config during preflight | Exact direct pin | scripts/requirements.txt |
| Helm | 3.15.4 | Provisioning tool | Versioned download + publisher SHA-256 verification | application/Dockerfile |
| kubectl | 1.30.0 | Existing API/backup tool | Versioned download + publisher checksum; local dbaas/kubectl:1.30.0 | application/Dockerfile, tools/kubectl/Dockerfile |
| Debian utility bases | 12.9-slim | WAL-G, kubectl, MinIO/mc runtime | Explicit release tag | Utility Dockerfiles |
| kind node | v1.30.0 | Existing destructive lab bootstrap | Explicit node tag | init.bash |
| Local Helm charts | 0.0.1 | Existing two chart families | Source controlled; no remote dependencies | Six Chart.yaml files |
| Rook operator value | v1.17.3 | Existing external storage configuration | Existing explicit tag retained | rook-config/values.yaml; missing gitlink metadata remains unresolved |
| Gitleaks | v8.24.3 | Secret scanning | Versioned CI image/default rules | .gitlab-ci.yml, .gitleaks.toml |
| Backend deployment artifact | YOUR_REGISTRY/dbaas-backend:0.1.0 | Operator packaging placeholder | Must replace with rebuilt private artifact | application/k8s/deploy.yaml |

## Selection evidence and compatibility boundary

- PostgreSQL remains on major 16; [16.6 release notes](https://www.postgresql.org/docs/release/16.6/) identify the selected minor. It is a reproducible baseline, not a claim of current security patch completeness.
- [Patroni 4.0.4 metadata](https://raw.githubusercontent.com/patroni/patroni/v4.0.4/setup.py) supports Python 3.11/3.12 and the kubernetes extra. Its [release history](https://raw.githubusercontent.com/patroni/patroni/v4.0.4/docs/releases.rst) establishes the primary role-label behavior in 4.x that these manifests require and PostgreSQL 16 handling inherited from 3.x. The existing image's actual Patroni version is unknown; mixed-version migration needs operator review.
- [PgCat v1.2.0 configuration](https://raw.githubusercontent.com/postgresml/pgcat/v1.2.0/pgcat.toml) contains the pool/routing/exporter configuration family used by the watcher. Its [Dockerfile](https://raw.githubusercontent.com/postgresml/pgcat/v1.2.0/Dockerfile) uses the root runtime identity; changing only the watcher UID would break private shared-file access.
- MinIO source tags retain the existing server/client command model. The [server go.mod](https://raw.githubusercontent.com/minio/minio/RELEASE.2025-04-22T22-12-26Z/go.mod) names Go 1.24.2; the [client source dependencies](https://raw.githubusercontent.com/minio/mc/RELEASE.2025-04-16T18-13-26Z/go.mod) are also versioned. Exact downloaded source bytes were hashed locally. Phase 3 built these recipes and ran the binaries; full integration evidence is tracked separately. Source builds report DEVELOPMENT.GOGET because release linker metadata is not injected; image tags/source SHA-256 identify the selected source.
- Public registry checks confirmed PgCat v1.2.0 and pgAdmin 9.3. The queried MinIO/mc release tags and bitnami/kubectl:1.30.0 were unavailable, so charts use local build recipes instead of those unavailable tags.

## Builds and reproducibility limits

Build from this working tree, publish to an operator-controlled registry, and override chart image names with those artifacts before deployment. The dbaas/* names denote local build outputs, not images published by this task. The lab init script builds/loads them but remains destructive and assumes Secrets are provisioned. For regular use, build each Dockerfile separately; do not run init.bash against wanted data.

Phase 3 built all seven repository-controlled images and ran selected binary checks; see the Phase 3 report for integration results. Registry metadata checks alone are not startup tests. Docker instruction/JSON/RUN-shell checks are not full BuildKit validation. Semantic/release tags were chosen for development ergonomics; for production, record immutable digests after trusted builds. Base tags, apt repositories, Python transitive dependencies and publisher-fetched Helm/kubectl checksums remain mutable inputs. WAL-G lacks archive checksum verification. Node 18 and these historical baselines require a separate supported-version/CVE review before production; this phase does not claim they are patched current releases.

The Phase 5 lab pins the kube-prometheus-stack chart and checksum in `scripts/resilience/dependencies.json` and installs its Prometheus Operator/Prometheus/Grafana stack. Loki, Fluent Bit, Traefik and cert-manager remain external references without comparable installation evidence. Production operators must record actual component image versions and supported upgrades separately. The local charts have no dependencies section, so Chart.lock is not applicable; the metadata appVersion values are legacy labels, not runtime versions.

Phase 3 moved utility runtimes from Debian 11.11 to 12.9 after observed Bullseye security-package 404 failures. [Bullseye LTS ended August 31, 2026](https://wiki.debian.org/LTS/Bullseye). Bookworm builds passed in this environment; image tags still do not establish complete dependency reproducibility.

Phase 3 also patched js-yaml to exact 4.3.2 after npm audit identified merge-key parsing advisories in 4.1.0. [Upstream release](https://github.com/nodeca/js-yaml/releases/tag/4.3.2). The updated lock installs 37 packages; npm audit reported zero vulnerabilities for this dependency set on the validation date.
