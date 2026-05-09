# Block 08 — Cross-Harness Patch Bundler

## Responsibility

Export one committed `ResourcePatch` as per-framework artefacts. A skill patch becomes a Claude Code `SKILL.md`, a Cursor rule, a LangGraph node snippet, a LobeHub agent JSON — all from the same underlying evolved resource.

Directly extends the pattern of [everything-claude-code](../../../../docs/62-everything-claude-code.md) from **content bundles** to **evolved content bundles**.

## Contract

```python
class Bundler:
    def bundle(self, patch: ResourcePatch, targets: list[BundleTarget]) -> list[BundleArtefact]
    def supported_targets(self) -> list[BundleTarget]

class BundleArtefact:
    target: BundleTarget     # "claude-code" | "cursor" | ...
    filename: str
    content: str
    checksum: str
```

## MVP targets (1)

Only `claude-code` SKILL.md is shipped in MVP. The bundler emits:

```markdown
---
name: <skill name>
description: <skill description>
source: gnomon-evolved
patch_id: <patch_id>
attribution_source: <attribution ref>
---

<skill body>
```

The `source: gnomon-evolved` tag is the marker that lets operators audit which parts of their Claude Code skill library came from Gnomon's evolution loop vs. hand-crafted.

## Roadmap targets (not in MVP)

- `cursor` — `.cursorrules` file format
- `codex` — Codex agent YAML
- `opencode` — OpenCode config
- `antigravity` — Antigravity agent spec
- `gemini` — Gemini Code Assist rule
- `langgraph` — node snippet
- `lobehub` — agent JSON
- `openclaw` — skill.md (same as Claude Code with extra fields)

## Why this matters

A patch evolved from a Claude Code trace can improve a Cursor user's experience with zero additional training. This is how Gnomon compounds beyond any single host framework — and why the 2026 cross-harness trend from [everything-claude-code](../../../../docs/62-everything-claude-code.md) fits naturally with the evolution loop.

## Non-goals for MVP

- Round-trip import (reading a Claude Code skill back into a `ResourcePatch`).
- Semantic mapping across frameworks (e.g. translating a LangGraph state machine into a Cursor rule set) — MVP is resource-type-preserving only.
- Bundler UI; operators commit patches via API in MVP.
