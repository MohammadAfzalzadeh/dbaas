#!/bin/bash

# Default values
PATRONI_RELEASE="patroni-mvp"
PGCAT_RELEASE="pgcat-mvp"
MINIO_RELEASE="minio-mvp"

# Parse command line arguments
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
    --minio-releasename)
      MINIO_RELEASE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check required values
#if [[ -z "$PATRONI_RELEASE" || -z "$PGCAT_RELEASE" || -z "$MINIO_RELEASE" ]]; then
#  echo "Usage: $0 --patroni-releasename NAME --pgcat-releasename NAME --minio-releasename NAME"
#  exit 1
#fi

# Paths to your custom Helm chart directories
PATRONI_CHART_PATH="./../helmCharts/patroni"
PGCAT_CHART_PATH="./../helmCharts/pgcat"
MINIO_CHART_PATH="./../helmCharts/minio"

# meta.helm.sh/release-name
# Helm deploy functions
deploy_chart() {
  local release=$1
  local chart_path=$2
  echo "📦 Installing or upgrading Helm release: $release from $chart_path"
  helm upgrade --install "$release" "$chart_path" -f "$chart_path/values.yaml" --namespace dbaas  --create-namespace
}

wait_for_jobs_success() {
  local release=$1
  local namespace="dbaas"
  echo "⏳ Waiting for jobs with annotation 'meta.helm.sh/release-name=$release' in namespace '$namespace'..."

  # Get job names with matching annotation
  local jobs=$(kubectl get jobs -n "$namespace" -o json | jq -r \
    --arg rel "$release" \
    '.items[] | select(.metadata.annotations["meta.helm.sh/release-name"] == $rel) | .metadata.name')

  if [[ -z "$jobs" ]]; then
    echo "⚠️  No jobs found with annotation meta.helm.sh/release-name=$release in namespace $namespace"
    return 0
  fi

  for job in $jobs; do
    echo "➡️  Waiting for job '$job' to complete..."
    kubectl wait --for=condition=complete job/"$job" -n "$namespace" --timeout=180s
    if [[ $? -ne 0 ]]; then
      echo "❌ Job '$job' failed or timed out."
      exit 1
    fi
  done

  echo "✅ All annotated jobs for release '$release' completed successfully."
}

# Wait for Patroni StatefulSet to be fully ready
wait_for_patroni_statefulset_ready() {
  local release=$1
  local namespace="dbaas"
  echo "🔍 Checking StatefulSet with labels application=patroni, release-name=$release..."

  local statefulset_name
  statefulset_name=$(kubectl get statefulsets -n "$namespace" \
    -l "application=patroni,release-name=$release" \
    -o jsonpath='{.items[0].metadata.name}')

  if [[ -z "$statefulset_name" ]]; then
    echo "❌ No StatefulSet found for Patroni release '$release'."
    exit 1
  fi

  echo "➡️  Waiting for StatefulSet '$statefulset_name' to become ready..."
  kubectl rollout status statefulset/"$statefulset_name" -n "$namespace" --timeout=180s
  if [[ $? -ne 0 ]]; then
    echo "❌ Patroni StatefulSet rollout failed or timed out."
    exit 1
  fi

  echo "✅ Patroni StatefulSet '$statefulset_name' is ready."
}
# Step 1: Deploy MinIO
deploy_chart "$MINIO_RELEASE" "$MINIO_CHART_PATH"

# Step 2: Wait for MinIO jobs to succeed
wait_for_jobs_success "$MINIO_RELEASE"

# Step 3: Deploy Patroni and wait to statefulSet come to ready
deploy_chart "$PATRONI_RELEASE" "$PATRONI_CHART_PATH"
wait_for_patroni_statefulset_ready "$PATRONI_RELEASE"
# Step 4: Deploy Pgcat
deploy_chart "$PGCAT_RELEASE" "$PGCAT_CHART_PATH"

echo "✅ All releases deployed successfully."
