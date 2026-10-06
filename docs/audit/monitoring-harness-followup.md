# Monitoring evidence follow-up

Classification: **STATICALLY VALIDATED**. Live rerun: **NOT VALIDATED**.

The completed Phase 5 investigation left a failed scrape-alert transition without enough diagnostic context. Reviewing its harness found three additional problems: repeat runs wrote to the same evidence paths, restoration failures could prevent samples from being saved, and the outer `kubectl exec` inherited a 900-second default despite the short alert observation windows.

## Changes

- `scripts/resilience/monitoring-checks.py`: allocate a new attempt directory; persist samples as they arrive; capture affected target health and full selected rule state; record preparation/fault/cleanup failures separately.
- Restore the exact original ServiceMonitor spec after any attempted fault PATCH, including a timeout whose server-side outcome is uncertain. Verify the restored spec and observe the resolved alert state.
- Preserve the original exception if restoration also fails. Store exception types and phases without arbitrary exception text. Cleanup success cannot override a failed experiment.
- Bound API exec and monitor read/PATCH commands to 20 seconds. Keep transition windows unchanged; increasing a timeout does not establish a root-cause fix.
- `tests/test_monitoring_evidence.py`: cover success, combined experiment/cleanup failure, uncertain PATCH outcome, baseline failure without mutation, and separate attempts after preparation failure.
- `docs/operations/phase5-continuation.md`: document the new evidence paths and limits.

## Validation

Five new regression tests exercise failure paths with simulated APIs and temporary evidence directories. The full 79-test Python suite, six Helm lints and syntax parsers passed. Results are retained in `results/validation/monitoring-harness/attempt-1/`. All 237 indexed historical runtime artifacts were checked against their saved hashes and remain unchanged.

No cluster was created or modified, no image source changed, and no commit or push was performed. Previous benchmark and runtime observations remain historical evidence rather than validation of this harness revision.

## Remaining issues

The historical replica-recovery cause and failed scrape-alert transition remain unresolved. A future owned-lab rerun must inspect the target scheme, scrape error and rule evaluation state before claiming a fix. Missing production instrumentation and external recovery validation remain outside this change.
