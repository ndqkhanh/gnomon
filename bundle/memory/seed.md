# Gnomon seed memory

## The 12 HIR primitives (canonical names)

| Primitive          | What it represents |
|--------------------|--------------------|
| `prompt`           | LLM input construction |
| `tool_call`        | function/tool invocation |
| `tool_result`      | tool return value |
| `context_compact`  | summary or eviction step |
| `permission_check` | guard before a destructive op |
| `hook_invocation`  | hook fire (pre/post tool, etc.) |
| `subagent_spawn`   | child agent creation |
| `memory_read`      | retrieve from memory store |
| `memory_write`     | store to memory store |
| `skill_load`       | load a SKILL.md into context |
| `verifier_run`     | run a verifier / evaluator |
| `commit`           | irreversible final step |

## Three known failure classes (v0.1)

- `compaction_loss` — fact eviction at `context_compact` step.
- `mis_permissioned` — wrong admit/deny at `permission_check`.
- `skill_miss` — wrong skill at `skill_load`.

## Cross-harness primitive renames (v0.1)

| Lyra              | Claude Code     | OpenClaw    | Hermes      |
|-------------------|-----------------|-------------|-------------|
| `context_compact` | `context_compact` | `summarize` | `digest`  |
| `permission_check`| `permission_check`| `guard`    | `policy`   |
| `skill_load`      | `skill_load`    | `lookup`    | `recall`    |

(Extend as new harnesses are catalogued.)
