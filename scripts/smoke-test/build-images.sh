#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
docker build -t dbaas/wal-g:3.0.7 wal-g
docker build -t dbaas/patroni:2.1.0 patroni
docker build -t dbaas/pgcat-config-watcher:1.1.1 pgcat
docker build -t dbaas/minio:RELEASE.2025-04-22T22-12-26Z minio
docker build -t dbaas/mc:RELEASE.2025-04-16T18-13-26Z -f minio/mc.Dockerfile minio
docker build -t dbaas/kubectl:1.30.0 tools/kubectl
docker build -t dbaas/backend:0.2.0 application
