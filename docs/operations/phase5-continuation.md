# Reproduce continuation checks

Use only an owned disposable lab and its private `--state-dir`. Each of these tools calls the cluster identity guard before mutation. Do not point them at production or the user's default context.

- `scripts/resilience/recovery-investigation.py`: complete timeline/slot/WAL/configuration snapshots, primary worker stop/return, automatic recovery, acknowledged-write retention. `--clients 4 --interval .01` increases the write stream; default is one client at a 0.1-second interval. No reinitialize is issued.
- `scripts/resilience/isolated-durability.py`: verify archive detachment, future source row exclusion, writable state, graceful and abrupt clone replacement.
- `scripts/resilience/proxy-shutdown.py`: capture per-container exit status, ready Service endpoints and persistent client results during graceful proxy deletion.
- `scripts/resilience/rotation-reload.py`: disposable-role password rotation with projected Secret/autoreload and held sessions.
- `scripts/resilience/alert-rehearsal.py`: scale the owned proxy Deployment to zero, stop PostgreSQL on a paused isolated clone, then create a real backup Job whose selector matches no primary. Restore workloads in `finally`; `--skip-proxy` permits a database/backup rerun after a completed proxy test.
- `scripts/resilience/promtool-check.py`: regression-test the real rules with the installed Prometheus binary.
- `scripts/resilience/restore-size.py --rows 100000` or `--rows 440000`: conservative deterministic payloads; actual relation bytes are measured. It refuses low host disk headroom and other sizes.
- `tools/reporting/summarize-continuation.py <runtime-directory>`: derive injection-aligned client transaction windows.

Attempts are allocated as `scenario/attempt-N` without replacing earlier directories. Abrupt termination of a host process can bypass Python cleanup: inspect the owned lab, restore paused/zero-scaled workloads, and use the lab cleanup stage before ending the work. Failed restore attempts can leave a payload table or target release; inspect the recorded attempt before removing anything.

The metrics-only Patroni Service and matching ServiceMonitor must be upgraded together. The SQL role Services are unchanged. Watcher 1.1.1 adds explicit shutdown handling while retaining the 90-second PgCat pod grace and its 60-second configured client-drain budget.

## Scrape-alert diagnostic follow-up

`monitoring-checks.py` now writes each dashboard/scrape-alert run under `monitoring-checks/attempt-N`. It persists alert samples immediately, records the failure stage and affected scrape targets, and attempts restoration even when the fault PATCH times out. A restoration failure is recorded separately and does not replace the original error. Successful cleanup does not turn a failed attempt into a success. Prometheus API exec and monitor PATCH/read commands have 20-second limits; the existing transition observation windows are unchanged.

These follow-up changes are **STATICALLY VALIDATED** with simulated API and cleanup failures. They have not been rerun in a live cluster. The recorded 90-second scrape-alert failure remains **FAILED**. See the [follow-up report](../audit/monitoring-harness-followup.md).
