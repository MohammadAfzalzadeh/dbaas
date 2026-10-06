# Phase 3 migration and immutable fields

No live resource migration is performed by this change. Phase 1 and Phase 2 are uncommitted baseline work; a deployment predating them may still need the migrations identified in their reports.

| Field/change | Patch behavior | Operator action |
|---|---|---|
| StatefulSet/Deployment selectors | Immutable; Phase 3 preserves baseline selectors | Old pre-Phase-1 controllers may need deliberate recreation with workloads stopped and PVCs retained |
| StatefulSet serviceName | Immutable; Phase 3 preserves baseline name | Old MinIO serviceName corrections require controller recreation; inventory claims first |
| volumeClaimTemplates class, capacity, accessModes, labels | Generally immutable on StatefulSet; no default identity change here | Do not apply overrides blindly to existing releases; use CSI expansion or migration and controlled controller recreation |
| podManagementPolicy | Immutable; explicit OrderedReady matches prior default | A customized Parallel deployment must retain its policy or use a planned recreation |
| updateStrategy, pod resources, probes, scheduling, grace | Mutable template/strategy fields | OnDelete requires manual pod replacement; hard scheduling can leave replacements Pending |
| PVC retention policy | Mutable where supported; opt-in >=1.27 | Keep Retain/Retain; check feature gate and PVC owner references |
| Service selectors | Mutable (not inherently immutable) | Endpoint changes immediately affect routing; preserve the selectorless Patroni DCS Service |
| Service clusterIP/headless form | Usually immutable | Recreate only in an approved outage; do not change Patroni-owned Endpoints independently |
| PDB/NetworkPolicy | Added resources | Render selectors and inspect eviction/network behavior before enabling restrictive rules |

For controlled recreation: export Helm values/manifests securely; list pod→PVC→PV identities and reclaim policies; verify off-cluster backup and restore; schedule an outage; prevent writes; scale/stop only the affected workload using a reviewed procedure; confirm volume unmount and retained claims; recreate controller with compatible selectors, serviceName and claim names; verify reattachment and database roles before allowing traffic. `helm upgrade --force`, blanket uninstall/reinstall and broad PVC deletion are not safe shortcuts.

A storage-class/access-mode change needs data copied/restored into new claims. Do not relabel unrelated claims to bypass ownership checks. Keep the old claims until restored data is verified. A rollback may require restoring data rather than reverting YAML.

Operational compatibility changes: PostgreSQL/MinIO now default to OnDelete; MinIO replicaCount must be 1; restrictive NetworkPolicy remains opt-in; recovery `--execute` additionally requires `--state-dir NEW_PRIVATE_DIRECTORY`; rebuilt local images must be loaded/published deliberately. Do not reuse an old cached image tag and assume its content changed. Use immutable registry digests for deployment promotion (still Planned).
