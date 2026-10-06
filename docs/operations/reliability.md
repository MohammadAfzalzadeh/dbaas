# Reliability model

Phase 3 strengthens the existing prototype. Phase 4 adds [runtime evidence](../audit/phase4-runtime-validation-report.md) from disposable kind. It does not establish production readiness, an SLA, or measured failover performance. See [validation evidence](../audit/phase3-reliability-report.md).

## Workloads and resources

Both `helmCharts/` and `application/helmCharts/` are active. The API bundles the latter. Raw `kuberResources/` manifests remain legacy; these reliability settings do not apply to them. Prometheus, Grafana, Loki and their storage are externally installed, not lifecycle-managed by these charts.

Every chart container, including WAL-G initialization, PgCat initialization/watcher, pgAdmin, MinIO initialization and backup dispatch, has configurable CPU/memory requests. Defaults are small development starting points, not capacity recommendations. Limits default to `{}`. Namespace LimitRanges/ResourceQuotas can add restrictions or reject pods. Production sizing must include PostgreSQL shared buffers, per-query work_mem multiplied by concurrency, autovacuum, replication, page cache and WAL-G memory. The backup container only runs kubectl: actual compression/upload consumes **PostgreSQL pod resources**. Tune database parameters and concurrency before imposing a database memory limit; an OOM can take down the primary.

Main values: `postgres.resources`, `walg.resources`, `backup.resources`, PgCat `resources`/`watcherResources`/`pgadmin.resources`, MinIO `minio.resources`/`minioInit.resources`. API resources are in `application/k8s/deploy.yaml`; use a deployment overlay for production. API remains one replica: temporary files are private and isolated, but provisioning has no durable job state or per-release distributed lock. Even one replica accepts concurrent requests; serialize operations targeting a release operationally.

## Scheduling and disruption

Each chart has a small scheduling helper. PostgreSQL and PgCat default to preferred anti-affinity on `kubernetes.io/hostname`. A single-node lab remains schedulable. Configure `antiAffinity: required` only when enough eligible nodes exist. `nodeSelector`, `tolerations`, `affinity` and `topologySpreadConstraints` are supported under each workload's `scheduling` values. Explicit affinity overrides generated anti-affinity; its selectors are operator-owned. Generated anti-affinity and spread selectors always include the release. Topology spread is opt-in; node/zone labels must exist.

Example PostgreSQL override (use top-level scheduling/replicaCount for PgCat):

```yaml
postgres:
  replicaCount: 3
  scheduling:
    antiAffinity: required
    topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
  resources:
    requests: {cpu: "1", memory: 2Gi}
```

This is an example scheduling profile, not a tested production capacity profile. Zone spreading is supported by changing the topology key to `topology.kubernetes.io/zone`; no multi-zone availability has been measured.

PDBs default to `maxUnavailable: 1` only when PostgreSQL/PgCat desired replicas exceed one. A single replica has no PDB and no redundancy. With two healthy pods one voluntary eviction is allowed, leaving one member; maintenance must wait for recovery before the next eviction. Three or more still permit only one eviction at a time. These are database members, not an etcd quorum. DCS availability depends on the Kubernetes control plane. PDBs cannot guarantee a primary survives, stop involuntary failures, or protect direct pod deletions and StatefulSet updates. An already-unready member can block a drain; repair it rather than force an eviction blindly.

## Probe semantics

| Workload | Startup | Readiness | Liveness |
|---|---|---|---|
| Patroni | `/health`, up to 360 × 10s by default | `/read-only`: running primary or load-balanced replica | `/liveness`, opt-in, disabled by default |
| PgCat | Config init must succeed; proxy startup failures restart its process | Watcher runs bounded `SELECT 1` through localhost PgCat using first configured DB/user | No dependency-driven liveness restart |
| FastAPI | `/healthz` | `/readyz`: token length, Helm/kubectl binaries and chart files | `/healthz`, process/application response |
| MinIO | `/minio/health/live`, 60 × 10s | `/minio/health/ready` | `/minio/health/live`, 6 failures |
| pgAdmin | `/misc/ping`, 60 × 10s | `/misc/ping` | None |
| Jobs/init containers | Process exit and deadline | Not applicable | None |

Patroni's role Services still select primary/replica separately. Readiness is not a replication-lag or RPO guarantee. Startup windows must exceed worst-case restore/base-clone time; increase `postgres.startupProbe.failureThreshold` or explicitly disable that probe during a reviewed long restore. Helm's deployment timeout is separate. Because Helm does not wait for OnDelete StatefulSet pod readiness, the API and recovery workflow explicitly wait for the desired ready member count. PgCat readiness tests one pool, not every database/user/shard; bad credentials or absent replicas may make it unready. PgCat config is per-pod emptyDir, so replicas do not share writable files. Client reconnection is required when a proxy pod disappears.

Probe choices follow [Patroni REST API semantics](https://patroni.readthedocs.io/en/rel_4_0/rest_api.html) and [MinIO health documentation](https://github.com/minio/minio/blob/master/docs/metrics/healthcheck/README.md).

## Termination

Patroni entrypoint uses exec; its Dockerfile explicitly overrides the PostgreSQL base image's SIGINT with SIGTERM. Patroni handles SIGTERM and performs its HA shutdown. Pods allow 180 seconds by default. No preStop script issues a competing switchover. Checkpoint/replication delays may require more time; exhaustion still leads to SIGKILL.

PgCat v1.2.0's upstream image declares SIGINT; its handler drains clients up to the generated 60-second shutdown timeout. SIGTERM exits immediately. Preserve that image stop signal when repackaging; runtime behavior remains to be measured. Pod grace is 90 seconds. The watcher may stop in parallel; proxy configuration remains on the pod volume. [PgCat source](https://github.com/postgresml/pgcat/blob/v1.2.0/src/main.rs), [image recipe](https://github.com/postgresml/pgcat/blob/v1.2.0/Dockerfile).

FastAPI runs Uvicorn with a 690-second graceful timeout and 720-second pod grace. One provisioning request may contain multiple sequential Helm calls and exceed this window. Kubernetes may kill it mid-operation; inspect completed releases before retrying. No durable transaction or automatic rollback is promised.

## Network policies and RBAC

NetworkPolicy templates default off. Opt-in requires explicit nonempty ingress/egress lists; `[{}]` deliberately allows all and is useful only for debugging. Rules select all pods carrying that chart release label, including backup/MinIO-init Jobs. This is a policy scaffold, not a tenant-isolation boundary. The API deployment is outside chart policy selection and needs an environment-specific policy.

Before enabling, allow DNS UDP/TCP 53, Patroni → Kubernetes API HTTPS (service and endpoint/NAT behavior depends on CNI), member replication TCP 5432, member REST TCP 8008, PgCat → database TCP 5432, WAL-G → MinIO TCP 9000 or external HTTPS 443, MinIO initialization → server, application clients → PgCat 5432, metrics scraping → configured PgCat metrics/Patroni/MinIO ports. API needs Kubernetes/Helm lifecycle access; backup pods need Kubernetes API for exec. Verify logging-agent collection and observability namespace selectors. Node/kubelet probe treatment depends on CNI. Never guess an external S3/API CIDR. Default kind networking does not demonstrate enforcement.

API Role remains namespaced and covers child Role creation, Secrets, workload lifecycle, PDB and optional NetworkPolicy operations. Kubernetes API bypass remains off; its cluster-scoped permissions require separate operator authorization. Backup exec permissions remain namespace-scoped but cannot be restricted by label through RBAC. The recovery CLI uses operator kubeconfig, not a new privileged ServiceAccount.

## Backup/recovery and remaining failure domains

CronJob defaults: Forbid overlap, one successful/three failed histories, one-hour scheduling delay allowance, six-hour job deadline, remote WAL-G timeout 21,000 seconds plus 60 seconds forced termination, one retry, one-day finished-job TTL. Increase both timeouts for large databases. The remote timeout is necessary because killing kubectl may leave its exec process running. Forbid applies only to the CronJob controller: manually created Jobs/execs can overlap. Failed uploads may leave objects; retention/pruning is operator-managed.

Recovery is explicit, destructive and nontransactional. CLI `--execute` now requires a **new** `--state-dir`. It holds mode-600 chart values and a stage journal in a mode-700 directory. Those values may contain development credentials: secure and delete the directory after verification. Failures report the stage and exact install commands for review. Do not replay deletion after a partial failure. Helm readiness does not prove recovered data or WAL coverage.

Default MinIO, PgCat and API each have one replica. MinIO uses one local volume and cannot be made distributed by raising replicaCount (the chart rejects it). External S3 is supported through existing WAL-G Secrets; disable MinIO provisioning when using it. Storage loss and a single-node Kubernetes control plane remain failure domains. No failover duration, RPO, RTO or availability number is asserted.

Phase 4 recovery stops the validated Patroni StatefulSet before uninstalling its Services: a running Patroni process can recreate its configuration Service and cause Helm uninstall to time out. Preflight rejects automatic PVC deletion on scale-down or uninstall; omitted policies default to Retain. Wait for pod deletion before DCS/PVC cleanup; do not bypass a failed shutdown or remove unrelated resources. See the [runtime report](../audit/phase4-runtime-validation-report.md).
