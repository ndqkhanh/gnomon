---
title: Gnomon — Skills (substrate)
description: Gnomon is the trace substrate; it produces HIR-derived skills via the gnomon evolution loop and exports them in the harness-skills format.
---

# Gnomon — Skills (substrate)

Gnomon is the **substrate**, not a consumer. The gnomon evolution loop
already produces SKILL.md patches for the Claude Code adapter; this doc
formalises the export so other projects can vendor the patches via the
shared `harness-skills` schema.

## Corner of the design space

| Axis | Value |
|---|---|
| Feedback signal | HIR-trace primitive-level attribution + Pass^k + mesa-guard |
| Skill artifact | `SKILL.md` per primitive recovery pattern |
| Parameter access | Substrate-level (no LLM training) |
| Reference paper | gnomon's own evolution-loop paper |

## Adapter

`gnomon` exports HIR traces and converts them to candidate skills via
`harness_skills.extract.TraceExtractor`. Other projects (lyra, orion-code)
consume these via the shared schema.

## Bright-lines

- gnomon's existing replay + Pass^k + mesa-guard are the discipline; no
  new bright-lines are required for the skills layer.

## Seed skills

- `recover-from-tool-fail` — retry pattern for primitive-tool failures.
- `recover-from-stale-memory` — re-fetch pattern for stale-memory reads.
