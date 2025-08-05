#!/bin/bash

set -euo pipefail

# Input parameters
PATRONI_RELEASE="patroni-mvp"
PGCAT_RELEASE="pgcat-mvp"
RECOVERY_TIME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --patroni-releasename)
      PATRONI_RELEASE="$2"
      shift 2
      ;;
    --pgcat-releasename)
      PGCAT_RELEASE="$2"
      shift 2
      ;;
    --recovery-time)
      RECOVERY_TIME="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate inputs
if [[ -z "$RECOVERY_TIME" ]]; then
  echo "Usage: $0 --recovery-time 'YYYY-MM-DD HH:MM:SS'"
  exit 1
fi

# Validate recovery time format (strictly 'YYYY-MM-DD HH:MM:SS')
if ! [[ "$RECOVERY_TIME" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]; then
  echo "❌ Invalid date format for recovery time. Expected 'YYYY-MM-DD HH:MM:SS'"
  exit 1
fi

NAMESPACE="default"
# Paths to your custom Helm chart directories
PATRONI_CHART_PATH="../helmCharts/patroni"
PGCAT_CHART_PATH="./helmCharts/pgcat"

# Functions
uninstall_release() {
  local release=$1
  echo "🗑 Uninstalling Helm release: $release"
  helm uninstall "$release" -n "$NAMESPACE" || true
}

delete_patroni_pvcs() {
  echo "🧹 Deleting PVCs for Patroni in namespace $NAMESPACE..."
  kubectl delete pvc -n "$NAMESPACE" -l "application=patroni,release-name=$PATRONI_RELEASE" || true
}

deploy_patroni_recovery() {
  echo "📦 Deploying Patroni in recovery mode to '$RECOVERY_TIME'"
  helm upgrade --install "$PATRONI_RELEASE" "$PATRONI_CHART_PATH" -n "$NAMESPACE" \
    --set postgres.BACKUP_ENABLE=true \
    --set postgres.RECOVERY_TARGET_TIME="$RECOVERY_TIME"
}

wait_for_patroni_ready() {
  echo "⏳ Waiting for Patroni StatefulSet to be ready..."
  local sts
  sts=$(kubectl get statefulset -n "$NAMESPACE" -l "application=patroni,release-name=$PATRONI_RELEASE" -o jsonpath='{.items[0].metadata.name}')

  if [[ -z "$sts" ]]; then
    echo "❌ Patroni StatefulSet not found."
    exit 1
  fi

  kubectl rollout status statefulset/"$sts" -n "$NAMESPACE" --timeout=180s
  echo "✅ Patroni is ready."
}

deploy_pgcat() {
  echo "📦 Deploying PgCat"
  helm upgrade --install "$PGCAT_RELEASE" "$PGCAT_CHART_PATH" -n "$NAMESPACE"
}

# Execution sequence
uninstall_release "$PGCAT_RELEASE"
uninstall_release "$PATRONI_RELEASE"
delete_patroni_pvcs
deploy_patroni_recovery
wait_for_patroni_ready
deploy_pgcat

echo "✅ Recovery completed successfully to time: $RECOVERY_TIME"
