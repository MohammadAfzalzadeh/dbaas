# Documentation

## Review paths

- **One minute:** [project overview](../README.md).
- **Management / hiring review:** [executive summary](report/executive-summary.md).
- **Engineering review:** [architecture](architecture/README.md), [canonical engineering report](report/engineering-report.md), [failure experiments](report/failure-engineering.md), [performance](report/performance-results.md).
- **Verify a claim:** [authoritative evidence index](evidence/README.md), [claims register](evidence/claims-register.md), [status matrix](evidence/project-status.md), [final checks](evidence/final-validation-summary.md).
- **Operate or extend:** [operations](operations/), [security](security/), [testing](testing/), [monitoring gaps](report/observability-gaps.md), [production gaps](report/production-gap-analysis.md).
- **Portfolio:** [LinkedIn](portfolio/linkedin-project.md), [carousel](portfolio/linkedin-carousel.md), [resume](portfolio/resume-project.md), [interview answers](portfolio/interview-talking-points.md), [STAR stories](portfolio/interview-stories.md).

## Reading historical material

[audit/](audit/) records each phase at its original validation boundary. Later findings are consolidated in the evidence index; historical PASS, FAILED and incomplete attempts remain visible under [results/](../results/). Earlier charts remain available, while [final charts](images/results/final/) use the continuation measurements. Do not combine different environments into a single success count.

The existing `helmCharts/` and `application/helmCharts/` locations remain unchanged for compatibility with scripts and the API. [Repository map](audit/repository-map.md) describes their responsibilities.
