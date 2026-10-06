# LinkedIn carousel outline

Ten slides; use concise captions and the actual exported assets below. Images illustrate architecture or measured data, never a fabricated running dashboard. Source and evidence links belong in speaker notes or the accompanying post.

## Slide 1: What I built

A PostgreSQL DBaaS prototype: UI → FastAPI → Helm → database services. State “disposable lab validation” on the slide.

[PNG](../images/architecture/architecture.png) · [SVG](../images/architecture/architecture.svg)

## Slide 2: Architecture

Separate provisioning responsibility from SQL, replication and recovery. All kind nodes share one host.

[PNG](../images/architecture/control-data-planes.png) · [SVG](../images/architecture/control-data-planes.svg)

## Slide 3: Provisioning/control plane

Validate inputs, authenticate, lint charts, deploy in order, wait for readiness and report partial completion.

[PNG](../images/architecture/provisioning-flow.png) · [SVG](../images/architecture/provisioning-flow.svg)

## Slide 4: HA and Patroni

Leadership, SQL readiness and client recovery are different milestones. PDBs govern voluntary evictions.

[PNG](../images/architecture/patroni-ha.png) · [SVG](../images/architecture/patroni-ha.svg)

## Slide 5: Backup and PITR

Base backup plus archived WAL; assert before/after-target data and a new write. Off-site recovery remains unvalidated.

[PNG](../images/architecture/pitr.png) · [SVG](../images/architecture/pitr.svg)

## Slide 6: Failure testing

Show measured promotion and client milestones from the continuation run; include the single-host qualification.

[PNG](../images/results/final/failover-timeline.png) · [SVG](../images/results/final/failover-timeline.svg)

## Slide 7: What broke

Explain watcher shutdown and archive separation corrections. Name the historical replica failure as unresolved despite three clean reruns.

[PNG](../images/architecture/graceful-shutdown.png) · [SVG](../images/architecture/graceful-shutdown.svg)

## Slide 8: Measured results

Use the backup comparison: 1,232 → 1,153 TPS, calculated 6.40% lower. One short paired observation.

[PNG](../images/results/final/backup-impact.png) · [SVG](../images/results/final/backup-impact.svg)

## Slide 9: What I learned

A passing command is insufficient: combine SQL assertions, object evidence, acknowledgements and recovery state.

[PNG](../images/architecture/validation-architecture.png) · [SVG](../images/architecture/validation-architecture.svg)

## Slide 10: Remaining production gaps

Independent storage/failure domains, off-site restore, durable control plane, complete telemetry, tenant identity and defined recovery objectives.

[PNG](../images/architecture/multinode-topology.png) · [SVG](../images/architecture/multinode-topology.svg)

## Evidence and export notes

Slide 6 uses [failover windows](../../results/runtime/multinode/dbaas-phase5-bc4cacdf48/failover-windows.json); slide 8 uses [backup measurements](../report/performance-results.md#backup-impact). Architectural sources are listed in the [diagram catalog](../architecture/README.md). Slide 7 is an explanatory diagram, not a trace of the unresolved replica failure. Use readable crops without removing axis units, measurement scope or limitation captions. See [production gaps](../report/production-gap-analysis.md) for slide 10.
