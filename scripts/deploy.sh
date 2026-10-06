#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CHARTS="$SCRIPT_DIR/../helmCharts"
PATRONI_RELEASE="patroni-mvp"
PGCAT_RELEASE="pgcat-mvp"
MINIO_RELEASE="minio-mvp"
NAMESPACE="dbaas"
while [[ $# -gt 0 ]]; do
  [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
  case "$1" in
    --namespace) NAMESPACE="$2" ;;
    --patroni-releasename) PATRONI_RELEASE="$2" ;;
    --pgcat-releasename) PGCAT_RELEASE="$2" ;;
    --minio-releasename) MINIO_RELEASE="$2" ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift 2
done
for name in "$NAMESPACE" "$PATRONI_RELEASE" "$PGCAT_RELEASE" "$MINIO_RELEASE"; do
  [[ "$name" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ && ${#name} -le 53 ]] || { echo "Invalid namespace/release" >&2; exit 1; }
done
helm upgrade --install "$MINIO_RELEASE" "$CHARTS/minio" -n "$NAMESPACE" --create-namespace --wait --wait-for-jobs --timeout 5m
helm upgrade --install "$PATRONI_RELEASE" "$CHARTS/patroni" -n "$NAMESPACE" --wait --wait-for-jobs --timeout 10m \
  --set-string "walg.AWS_ENDPOINT=http://$MINIO_RELEASE-minio:9000"
helm upgrade --install "$PGCAT_RELEASE" "$CHARTS/pgcat" -n "$NAMESPACE" --wait --wait-for-jobs --timeout 5m \
  --set-string "patroniReleaseName=$PATRONI_RELEASE"
echo "All Helm commands completed successfully. Live database/routing/backup verification is still required."
