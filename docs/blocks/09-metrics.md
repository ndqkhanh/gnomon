# Block 09 — Metrics & Decorrelation Dashboard

## Responsibility

Expose the operator-facing signals:

- Primitive coverage — which of the 12 primitives have been attributed to recent failures, over what time window.
- Attribution volume — failures per primitive over time (should trend down as evolution runs).
- Pass^k on replay set — the SLA-facing reliability metric.
- Pairwise decorrelation — per [docs/53](../../../../docs/53-chaos-engineering-next-era.md), the population-reliability signal.
- Evolution throughput — patches proposed / committed / rolled-back.

## Contract

```python
class Metrics:
    def primitive_coverage(self, tenant: str, window_hours: int) -> dict[HIRPrimitive, int]
    def attribution_volume(self, tenant: str, primitive: HIRPrimitive, window_hours: int) -> int
    def pass_pow_k(self, tenant: str, k: int, window_hours: int) -> float
    def decorrelation(self, tenant: str, instance_a: str, instance_b: str) -> float
    def evolution_stats(self, tenant: str, window_hours: int) -> EvolutionStats
```

## Decorrelation

Reuses the implementation shipping in [Vertex-Eval `sla.pairwise_decorrelation`](../../../vertex-eval/src/vertex_eval/sla.py). Population reliability depends on failure decorrelation between agent instances; highly-correlated failures (e.g. all instances fail on the same prompt-injection class) predict fleet-wide outages.

## Primitive coverage as a health signal

Two meanings:

1. **Coverage of attributions** — a harness that attributes failures to only 2 of 12 primitives is either very healthy or very unmonitored. The operator needs to know which.
2. **Coverage of evolution** — a patch history that exclusively touches `skill_invocation` is gaming the metric. The evolution-loop gate enforces primitive-diversity over time.

## Dashboard (MVP: API only; no UI)

MVP exposes metrics via `GET /v1/metrics` returning JSON. A post-MVP web dashboard renders primitive coverage as a 12-bar histogram per tenant, attribution volume as time series, decorrelation as a heatmap. The metrics API is designed so that existing Grafana / Prometheus deployments can scrape directly.

## Non-goals for MVP

- Web UI.
- Alerting integrations (PagerDuty / Slack).
- Cross-tenant aggregate views.
