# Block 07 — Replay Harness

## Responsibility

Given a HIR trace + a candidate `ResourcePatch`, re-execute the trace in a sandbox with the patched resource in place and compute the deltas (pass@k, pass^k, attribution volume per primitive).

## Contract

```python
class Replay:
    def replay_one(self, trace_id: str, patch: ResourcePatch, seed: int = 0) -> ReplayResult
    def replay_batch(self, trace_ids: list[str], patch: ResourcePatch, seed: int = 0) -> BatchReplayResult

class ReplayResult:
    original_trace_id: str
    replayed_trace_id: str
    success: bool
    attributions: list[Attribution]
    elapsed_ms: int
```

## Determinism

Seeded RNG + a `SyntheticLLM` (see below) make replays reproducible. The same `(trace, patch, seed)` always produces the same `ReplayResult`.

## SyntheticLLM

The replay sandbox's LLM is **not** a real API call in MVP. Instead, `SyntheticLLM` returns canned responses keyed on `(event.primitive, event.inputs_hash, patch.resource_uri)`. This means replay results are deterministic across machines and CI.

Production deployments can swap `SyntheticLLM` for a real LLM — the gate decision logic is unchanged; only the replay implementation varies.

## Attribution delta

For each replay, HAFC runs on both the original trace and the replayed trace. The diff — `attributions_before` vs `attributions_after` — is the evolution loop's primary signal. If the patch targets `compaction_loss` attributions and the replay has fewer of them, the patch is doing its job.

## Sandbox

The replay sandbox does not execute the host framework's real tools. Tool-use events are replayed from the original trace's outputs, which is why determinism is achievable. This is a deliberate trade-off: we cannot catch emergent behaviour that depends on fresh tool calls, but we gain zero-risk evaluation and reproducibility.

Post-MVP: add a "live replay" mode that re-invokes tools — gated behind explicit operator approval because of the blast-radius change.

## Pairwise comparison

`replay_batch` runs the same patch across N traces, producing N `ReplayResult` objects. The gate's Pass^k computation ([docs/38 Claw-Eval](../../../../docs/38-claw-eval.md), [Vertex-Eval passk](../../../vertex-eval/src/vertex_eval/passk.py)) operates on this batch.

## Non-goals for MVP

- Live-replay mode (no real tool calls).
- Replay against multi-framework traces simultaneously.
- Persistent replay artefacts (results are ephemeral in MVP).
