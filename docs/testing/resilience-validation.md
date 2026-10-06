# Phase 5 resilience laboratory

This is a staged, destructive experiment **only inside a newly created task-owned kind cluster**. It never uses the default kubeconfig. The existing `kind` cluster is unrelated. Requirements: Docker, kind, kubectl, Helm, Python/PyYAML, seven built images, and enough free memory/disk for four Kubernetes nodes. The recorded host exposed 12 CPUs and about 30 GiB RAM; this is shared host capacity, not dedicated pod capacity.

## Reproduce

Build with `bash scripts/smoke-test/build-images.sh`. Fetch pinned public dependencies with `python3 scripts/resilience/fetch-dependencies.py --directory /tmp/phase5-dependencies`. Review `dependencies.json` before changing a pin. No cloud credentials are required.

```bash
state=/tmp/my-dbaas-phase5-run
python3 scripts/resilience/lab.py setup --state-dir "$state" \
  --calico-manifest /tmp/phase5-dependencies/calico.yaml
python3 scripts/resilience/lab.py baseline --state-dir "$state"
python3 scripts/resilience/lab.py restore --state-dir "$state"
python3 scripts/resilience/lab.py network --state-dir "$state"
python3 scripts/resilience/lab.py disruptions --state-dir "$state"
python3 scripts/resilience/lab.py proxy_failure --state-dir "$state"
python3 scripts/resilience/lab.py rotation --state-dir "$state"
PROMETHEUS_CHART=/tmp/phase5-dependencies/kube-prometheus-stack-58.7.2.tgz \
  python3 scripts/resilience/lab.py observability --state-dir "$state"
python3 scripts/resilience/lab.py benchmarks --state-dir "$state"
python3 scripts/resilience/lab.py cleanup --state-dir "$state"
```

Run stages individually and stop dependent experiments after a failure. **Always run cleanup**, including after an interrupted stage; private state is deliberately retained for diagnosis until cleanup. Setup refuses an existing state directory. Subsequent stages verify both node names and the kube-system namespace UID. Cleanup deletes only the recorded cluster and removes private credentials. Do not copy `/tmp/.../credentials.json`, kubeconfig, or Helm value files into evidence.

On this host, inotify exhaustion required the explicit setup option `--temporary-inotify-limit 1024`. This changes a host-wide kernel setting through a privileged disposable utility container. Record the original value; cleanup restores it. Do not change it blindly on shared hosts. The recorded run began at 128 and used 1024 temporarily.

## Interpretation

Calico enforces policies. Database members use three distinct workers; PgCat uses two. Local-path PVCs remain tied to their original node. Draining a node can leave its replacement database pod Pending until the node is uncordoned. PDBs govern voluntary eviction, not abrupt node loss, storage redundancy, or application consistency.

The persistent client commits unique transaction IDs and then records acknowledgements. Failed or timed-out transactions are not assumed rolled back and are not replayed. `longest_success_gap_seconds` includes the configured sampling interval; it is not an exact outage duration. Reconnect counts describe this client, not transparent session migration by PgCat. The final abrupt-proxy client uses libpq `tcp_user_timeout=5000` as well as keepalives; earlier node-loss/drain samples predate that setting. Its first abrupt-proxy attempt stalled without the TCP user timeout.

The original drain timer polls promotion only after drain completes. Its promotion/SQL observations are upper bounds that include PgCat's graceful termination period. Use the timestamped client samples to describe transaction interruption. Internal Patroni failure-detection time is not separately instrumented.

The first Phase 5 node-loss run required manual replica reinitialization and exposed a clone restart defect. Preserve failed attempts; do not rerun a stage over its artifacts without archiving them. Consult the [Phase 5 report](../audit/phase5-resilience-evidence-report.md) before assuming the complete sequence passes unattended.

## Benchmark boundary

The suite runs PostgreSQL 16 pgbench, scale 1, concurrency 1/10/25/50, direct and PgCat routes, three profiles, ten seconds per sample. It resets logical balances between samples but does not cold-start caches. It uses one sample per point, four client threads at most, and no p95/p99 estimates. Read-heavy mixes nine selects per one simple update by weight; write-heavy uses simple-update; mixed uses tpcb-like. Pool size is 60 per proxy and the configuration rehearsal raises PostgreSQL max_connections to 200. Results are shared-host observations, not capacity estimates.

[PostgreSQL pgbench reference](https://www.postgresql.org/docs/16/pgbench.html) describes built-in scripts and reported statistics. Missing reconnect/percentile measurements are JSON null, never zero.

## Pooling mode and additional evidence

The final mixed-workload benchmark uses **transaction** pooling. The historical chart default is **session** pooling; a session that first selected a replica later rejected UPDATE in the recorded weighted workload. Aborted outputs are retained and excluded from throughput charts. Do not infer transaction-mode compatibility for every SQL feature. The initial disruption/rotation experiments used session mode; the final matrix and any later proxy rerun state their mode explicitly.

After monitoring, run `python3 scripts/resilience/monitoring-checks.py --state-dir "$state"` for real dashboard queries and the safe TLS scrape-failure alert rehearsal. After benchmarks, `python3 scripts/resilience/restore-size.py --state-dir "$state"` accepts `--rows 100000` or `--rows 440000`, creates a bounded compressible dataset and restores it to a new release. The continuation recorded approximately 113.8 and 500.7 MiB relations; these two samples do not establish a scaling curve. These scripts require the same owned cluster and private state. Always finish with cleanup.
