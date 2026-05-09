# Block 01 — Harness IR (HIR) Schema

## Responsibility

Define the lossless post-hoc schema every framework's traces normalise into. Twelve primitives drawn from the corpus; every HIR event carries enough context to drive attribution and replay.

## Shape

```python
class HIREvent:
    event_id: str             # hash-stable; "ev_<sha256[:12]>"
    run_id: str               # ties events in one execution
    tenant: str
    primitive: HIRPrimitive   # enum of 12
    ts_ms: int                # monotonic timestamp
    parent_id: Optional[str]  # parent frame for nested calls
    inputs: dict
    outputs: dict
    latency_ms: int
    cost_tokens: int = 0
    native_frame: dict = {}   # untranslated framework-specific record
    prev_digest: str          # hash-chain link
```

## The 12 primitives (anchors)

| Primitive | Corpus anchor |
|---|---|
| `agent_loop` | [docs/01](../../../../docs/01-agent-loop-architecture.md) |
| `subagent_delegation` | [docs/02](../../../../docs/02-subagent-delegation.md) |
| `plan_mode` | [docs/03](../../../../docs/03-plan-mode.md) |
| `skill_invocation` | [docs/04](../../../../docs/04-skills.md), [docs/19](../../../../docs/19-voyager-skill-libraries.md) |
| `hook` | [docs/05](../../../../docs/05-hooks.md) |
| `permission_check` | [docs/06](../../../../docs/06-permission-modes.md) |
| `tool_use` | ubiquitous |
| `compaction_event` | [docs/08](../../../../docs/08-context-compaction.md) |
| `memory_read` / `memory_write` | [docs/09](../../../../docs/09-memory-files.md) |
| `verifier_call` | [docs/11](../../../../docs/11-verifier-evaluator-loops.md) |
| `todo_scratchpad` | [docs/12](../../../../docs/12-todo-scratchpad-state.md) |
| `evolution_patch` | [docs/36](../../../../docs/36-autogenesis-self-evolving-agents.md), [docs/57](../../../../docs/57-sea-arxiv-2604-15034.md) |

## Invariants

- Every `event_id` must be unique within a trace; duplicates are ingest errors.
- `parent_id` must reference an earlier event in the same trace or be `None`.
- `ts_ms` must be monotonic across the trace.
- `prev_digest` chains events: `prev_digest_n = sha256(prev_digest_{n-1} || canonical_json(event_n-1))`.

## Non-goals

- HIR is **not** an authoring format. No framework is expected to rewrite its internal representation. Adapters convert post-hoc.
- HIR does **not** store raw payloads beyond the `native_frame` — no full conversation corpora, which would blow out storage.
