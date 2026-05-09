# Block 04 — Stochastic Harness Perturbation (SHP)

## Responsibility

Inject controlled, deterministic faults per HIR primitive. The chaos substrate that [docs/53](../../../../docs/53-chaos-engineering-next-era.md) calls for but no framework today implements. Produces labeled training data for HAFC and stress-tests committed patches.

## Contract

```python
class SHP:
    def inject(self, trace: list[HIREvent], injector: str, seed: int) -> list[HIREvent]
    def available_injectors(self) -> list[InjectorSpec]
    def describe(self, injector: str) -> str
```

## MVP injectors (2)

### `tool_use.latency_spike`

Wraps a `tool_use` event; multiplies `latency_ms` by a factor drawn from `seed`. Useful for testing whether downstream logic times out gracefully or blocks the loop.

### `memory_read.stale_fact`

Replaces `memory_read.outputs` with content from an older trace snapshot — simulates the "cache returned a stale result" failure that is very common in production and invisible to normal trace inspection.

## Roadmap injectors (not in MVP)

- `compaction_event.drop_random_span`
- `compaction_event.drop_recent_span`
- `compaction_event.fabricate_plausible_span`
- `permission_check.denied_on_legitimate`
- `permission_check.allowed_on_destructive`
- `plan_mode.stale`
- `subagent_delegation.handoff_corrupt`
- `tool_use.partial_result`
- `tool_use.wrong_result_right_format`
- `verifier_call.false_pass`

## Determinism

Every injector takes a `seed`; injector output is a pure function of `(trace, injector, seed)`. This means chaos runs are **reproducible** — you can re-play the same perturbation when debugging a patch regression.

## How SHP feeds HAFC

Each perturbed trace carries a `synthetic_failure_label` metadata field recording what SHP changed. HAFC training set uses these labels as ground truth — when HAFC's attribution aligns with the synthetic label, the classifier is correct.

## Non-goals for MVP

- Live production fault injection (this is a replay-only substrate in MVP).
- Injector composition (chaining two injectors).
- UI for operator to browse available injectors.
