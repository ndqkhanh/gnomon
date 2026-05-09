# Block 03 — Harness-Aware Failure Classifier (HAFC)

## Responsibility

Given a HIR trace + a rubric-style pass/fail signal, emit **primitive-level failure attributions** — not "the trace failed" but "the compaction layer dropped the fact on turn 7" or "the permission engine denied a legitimate action."

## Contract

```python
class HAFC:
    def attribute(self, trace: list[HIREvent], rubric_result: Optional[RubricResult] = None) -> AttributionReport

class Attribution:
    primitive: HIRPrimitive
    failure_class: FailureClass   # 12 classes, see below
    event_id: str                 # the HIR event implicated
    quote: str                    # short causal quote
    confidence: float             # [0, 1]
    channels_agree: bool          # cross-channel evidence
    suggested_patch_class: PatchClass
```

## Failure classes (12)

- `dropped_context` — compaction removed a needed fact
- `stale_memory` — memory_read returned outdated content
- `mis_permissioned` — permission_check blocked legitimate action OR allowed destructive without escalation
- `plan_bypass` — plan_mode gate was not respected
- `unverified_claim` — verifier_call absent where needed
- `tool_misuse` — wrong tool / wrong args
- `skill_miss` — skill_invocation failed to match / returned unrelated
- `subagent_handoff` — delegated sub-trace failed to return usable output
- `compaction_loss` — compaction_event removed fact later needed
- `reward_hack` — mesa-pattern detected (universal hammer, trivial closer)
- `resource_exhaustion` — run out of tokens / budget
- `prompt_injection` — adversarial input in an inbound channel

## Classifier strategy

### MVP — heuristic layer

- Rule-based classifiers per primitive. Example: `compaction_loss` fires when a `compaction_event` drops an event whose outputs are later referenced by a `memory_read` that returns empty.
- Cross-channel evidence — attribution only **confirmed** when ≥ 2 of {trace, audit, state-snapshot} agree.
- Mesa-guard generalisation from Quanta-Proof: reject attributions that would over-attribute a single primitive (universal-hammer detection).

### Roadmap — LLM judge ensemble

Swap heuristics for multi-family LLM judges (same shape as [Vertex-Eval](../../../vertex-eval/src/vertex_eval/judges.py)). Judges vote by majority; ensemble outputs the attribution. Human calibration loop labels a 200-trace gold set for regression testing.

## Output shape

```python
class AttributionReport:
    trace_id: str
    attributions: list[Attribution]
    cross_channel_confirmed: bool
    mesa_flagged: bool
    mesa_reason: Optional[str]
```

## Non-goals for MVP

- Real-LLM judges.
- Per-tenant custom classifiers.
- Human-in-the-loop labeling UI.
