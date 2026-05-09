# Block 06 — Evolution Loop Orchestrator

## Responsibility

The closed loop that makes the harness get better over time. Propose → assess → commit → rollback, over HIR traces with primitive-attributed failures as the reward signal.

## Contract

```python
class EvolutionLoop:
    def propose(self, attribution: Attribution) -> Optional[ResourcePatch]
    def assess(self, patch: ResourcePatch, replay_traces: list[str]) -> GateDecision
    def commit(self, patch: ResourcePatch) -> bool
    def rollback(self, patch_id: str, reason: str) -> bool
```

## Proposal rules (MVP)

- On attribution `skill_miss` with `suggested_patch_class = "extend_skill"`: propose a patch that adds a new trigger phrase or broadens the skill's description.
- On attribution `compaction_loss` with `suggested_patch_class = "pin_fact"`: propose a patch that adds a `memory_write` with `pinned: true` before the compaction event.
- On attribution `mis_permissioned` with `suggested_patch_class = "narrow_permission"`: propose a patch that tightens a permission rule's scope.

In MVP, only the first rule ships a real patch (resource_type=`skill`); the other two emit logs noting "would patch" but don't yet construct the diff.

## Gate decision

```python
class GateDecision:
    accepted: bool
    reason: str
    pass_pow_k_before: float
    pass_pow_k_after: float
    attribution_volume_before: int
    attribution_volume_after: int
    mesa_flagged: bool
```

Acceptance requires **all four**:

1. `pass_pow_k_after >= pass_pow_k_before + 0.02` (non-regression + small improvement)
2. `attribution_volume_after < attribution_volume_before` on the target primitive
3. `mesa_flagged == False` (no universal-hammer / trivial-closer)
4. Second-family judge agrees (MVP: always True; roadmap: real-LLM judge)

## Rollback

Rollback is a write to the resource store setting `status = rolled_back`. Subsequent reads of the resource return the ancestor. The rollback record is kept in the audit log; an operator can trace which regression triggered which rollback.

## Why this is the SEA breakthrough

Voyager's reward: task success in Minecraft. Hermes's: skill-reuse rate. ACE's: judge score. All proxy for improvement, none shared across systems. Gnomon's reward: **primitive-attributed failure rate going down per primitive**. This is the first **shared reward** that makes SEA systems comparable.

## Primitive coverage as a guard

Over any 30-day window, the gate rejects patches that would push the *distribution* of committed patches too heavily onto a single primitive. This resists the universal-hammer mesa pattern by forcing attention to spread across primitives. Generalised from the Quanta-Proof mesa-guard.
