#!/usr/bin/env bash
# Preparation only by default. Use only in an approved test cluster.
set -euo pipefail
[[ $# -ge 3 ]] || { echo 'Usage: failure-test.sh ACTION NAMESPACE PATRONI_RELEASE [PGCAT_RELEASE]' >&2; exit 2; }
action=$1; namespace=$2; release=$3; pool=${4:-}
for value in "$namespace" "$release"; do
  [[ "$value" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || exit 2
done
case "$action" in
  primary-delete|replica-delete)
    role=${action%-delete}
    mapfile -t targets < <(kubectl -n "$namespace" get pods -l "application=patroni,release-name=$release,cluster-name=$release-patronimvp,role=$role" -o name)
    [[ ${#targets[@]} -eq 1 ]] || { echo 'Expected exactly one target; select explicitly for larger clusters' >&2; exit 1; }
    command=(kubectl -n "$namespace" delete "${targets[0]}" --wait=true);;
  pgcat-restart)
    [[ "$pool" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || exit 2
    command=(kubectl -n "$namespace" rollout restart "deployment/$pool-proxy-deployment");;
  backup-during-workload)
    command=(kubectl -n "$namespace" create job "$release-experiment-$(date +%s)" "--from=cronjob/$release-exec-script-cronjob");;
  recovery)
    echo 'Use scripts/ptr_recovery.sh --dry-run first; execute requires --state-dir and a reviewed UTC target.'; exit 0;;
  *) echo 'Unknown action' >&2; exit 2;;
esac
printf 'Planned command: '; printf '%q ' "${command[@]}"; printf '\n'
[[ ${RUN_FAILURE_TEST:-0} == 1 ]] || { echo 'Preparation only. RUN_FAILURE_TEST=1 enables the printed mutation.'; exit 0; }
"${command[@]}"
