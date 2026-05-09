# Gnomon

**Harness-aware evaluator + closed evolution loop, exposed as a portable Harness IR.**

The sundial's gnomon casts the shadow that reveals the hour. In Gnomon, the attribution engine casts the shadow that reveals *which harness primitive* actually failed — making invisible primitive-level failures legible, and making the evolution loop's reward signal portable across every agent harness.

Design: [docs/architecture.md](docs/architecture.md) · [docs/architecture-tradeoff.md](docs/architecture-tradeoff.md) · [docs/system-design.md](docs/system-design.md) · [blocks/](docs/blocks/)

Breakthrough proposal: [../../docs/67-recommended-breakthrough-project.md](../../docs/67-recommended-breakthrough-project.md)

## What Gnomon does

1. **Ingests** traces from any agent harness (Claude Code adapter ships in MVP; LangGraph / Archon / DeerFlow / RAGFlow / LobeHub / OpenClaw on the roadmap).
2. **Normalises** them into a 12-primitive Harness IR — the first portable schema for agent-harness execution.
3. **Attributes** every failure to the specific primitive that caused it (compaction dropped a fact, permission blocked a legitimate action, plan was stale, skill didn't match, etc.) — not just "the trace failed."
4. **Injects chaos** per primitive (tool-latency spikes, stale memory reads, more on roadmap) to stress-test recovery paths and label training data for the classifier.
5. **Evolves** the harness by proposing Autogenesis-shaped resource patches, gating them via replay + Pass^k + mesa-guard, committing on accept, rolling back on regression.
6. **Bundles** committed patches as per-framework artefacts (Claude Code SKILL.md in MVP) so an evolution in one framework can improve another.

## MVP shape

- **10 source modules** in `src/gnomon/`: `models`, `hir`, `adapters`, `store`, `hafc`, `shp`, `patches`, `replay`, `evolution`, `bundler`, `metrics`, `app`.
- **66 unit tests** cover HIR chain-integrity, adapters, tenant isolation, attribution for 3 failure classes, chaos injection determinism, patch lifecycle, replay behaviour, gate decisions, bundler output, metrics, and the FastAPI HTTP surface.
- **HTTP API** with 10 endpoints: ingest (native + Claude Code), attribute, chaos inject, patch propose/commit/rollback, bundle, metrics.
- **Per-tenant isolation**, PII-redactor-compatible, hash-chained append-only audit log.

## Run locally

```bash
make install        # creates .venv, installs vendored ./harness_core + project editable
make test           # 66 unit tests, no API keys required
make run            # http://localhost:8011/docs (FastAPI with uvicorn --reload)
```

Port 8011 by default; override with `GNOMON_PORT=… make docker-up`.

## Docker

```bash
make docker-up
make docker-logs
make docker-down
```

The Containerfile vendors `harness_core/` so the build is fully self-contained.

## Example: ingest → attribute → propose → commit → bundle

```bash
# 1. Ingest a Claude Code trace export
curl -s localhost:8011/v1/ingest/claude-code -H 'content-type: application/json' -d '{
  "payload": {
    "trace_id": "cc_demo",
    "tenant": "acme",
    "entries": [
      {"kind": "user_message", "text": "draft my weekly review"},
      {"kind": "skill_invocation", "skill": "weekly_review", "matched": false}
    ]
  }
}'

# 2. Attribute — HAFC reports the skill_miss
curl -s localhost:8011/v1/attribute -d '{"trace_id":"cc_demo"}' -H 'content-type: application/json'

# 3. Propose a patch (extends the skill with a new trigger phrase)
curl -s localhost:8011/v1/patches/propose \
  -d '{"trace_id":"cc_demo","attribution_index":0}' \
  -H 'content-type: application/json'

# 4. Commit with a replay gate
curl -s localhost:8011/v1/patches/commit \
  -d '{"patch_id":"patch_xxx","replay_trace_ids":["cc_demo"]}' \
  -H 'content-type: application/json'

# 5. Bundle as a Claude Code SKILL.md
curl -s localhost:8011/v1/bundle \
  -d '{"patch_id":"patch_xxx","targets":["claude-code"]}' \
  -H 'content-type: application/json'
```

## The 12 HIR primitives

`agent_loop`, `subagent_delegation`, `plan_mode`, `skill_invocation`, `hook`, `permission_check`, `tool_use`, `compaction_event`, `memory_read`, `memory_write`, `verifier_call`, `todo_scratchpad`, `evolution_patch` — drawn directly from the research corpus's independent landmark files (`docs/01`–`docs/12`, `docs/36`, `docs/57`).

## The three failure classes in MVP

- **`compaction_loss`** — a compaction event dropped content the agent later needed.
- **`mis_permissioned`** — a permission check either blocked a legitimate action (deny-then-overturn) or allowed a destructive action without HITL.
- **`skill_miss`** — a skill invocation failed to match a user's intent.

Nine more classes are declared in the enum and waiting for classifiers: `dropped_context`, `stale_memory`, `plan_bypass`, `unverified_claim`, `tool_misuse`, `subagent_handoff`, `reward_hack`, `resource_exhaustion`, `prompt_injection`.

## Design grounding

- Harness IR primitives → corpus docs 01–12, 36, 57
- Attribution as shared SEA reward → docs 56, 57, 58, 59
- Cross-channel evidence → doc 38 (Claw-Eval)
- HORIZON-style failure attribution → doc 27
- Autogenesis resource patches → docs 36, 57
- Chaos injection → docs 49, 53
- Cross-harness bundling → doc 62 (everything-claude-code)
- Meta-harness landscape context → doc 66

## Status

Walking-skeleton MVP, April 2026. Not intended for production without further hardening (LLM-judge HAFC, additional framework adapters, additional injectors, real replay sandbox with live tools, SOC2 posture, signed-patch enforcement).

## TUI

A polished terminal interface ships out of the box, powered by the shared
[`harness-tui`](../../packages/harness-tui) package.

```bash
make install     # installs harness-tui editable alongside this project
make tui         # opens the TUI against the running FastAPI backend
make tui-mock    # demo: scripted events, no backend needed
```

Features:

- **Brand theme** with project ASCII logo + spinner pack.
- **Hero sidebar widget**: HIR primitive × framework failure heatmap.
- 16 built-in slash commands: `/help`, `/plan`, `/why`, `/cost`, `/recipe`,
  `/test`, `/find`, `/voice`, `/theme`, `/resume`, `/clear`, `/auto`,
  `/default`, `/quit`, `/cost tool`, `/cost agent`.
- Differentiators built in:
  - Stacked context-budget bar (system / files / conversation / output).
  - Latency sparkline with TTFT + inter-token measurements.
  - Per-tool / per-subagent token + cost rollup table.
  - Typed `Plan` editor (reorder + edit before execution).
  - Per-hunk diff approval (`y/n/a/d/q`).
  - Permission gates with blast-radius preview (dry-run output).
  - Auto-test / auto-lint loop (`/test on`).
  - Recipes (Goose-style YAML) under `recipes/`.
  - Transcript search (`Ctrl+F`).
  - Dual-cursor composer (input + agent quick-replies).
  - Voice mode (`F9` push-to-talk; `pip install 'harness-tui[voice]'`).
  - Web mode (`--serve` via `textual-serve`).
  - SSH mode (`--ssh` via `asyncssh`).
- **Visual snapshot tests** in CI — every PR diffs the SVG-rendered TUI.

See [`research/tui-state-of-the-art.md`](../../research/tui-state-of-the-art.md)
and [`research/tui-framework-and-rollout.md`](../../research/tui-framework-and-rollout.md)
for the design.
