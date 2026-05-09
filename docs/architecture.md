# Gnomon — Architecture

## What Gnomon is

Gnomon is a **harness-aware evaluator with a built-in closed evolution loop, exposed as a portable Harness IR (HIR)**. It ingests traces from any agent harness (Claude Code, LangGraph, Archon, DeerFlow, RAGFlow, LobeHub, OpenClaw), normalises them into a 12-primitive intermediate representation, attributes every failure to a specific harness primitive (not just "the trace failed"), and emits reversible Autogenesis-shaped resource patches back to the host harness — committing them under a gated propose → assess → commit → rollback loop.

Gnomon is the synthesis artefact for the 67-file research corpus at [../../../docs/](../../../docs/README.md). See [docs/67 — Recommended Breakthrough Project](../../../docs/67-recommended-breakthrough-project.md) for the original proposal.

## Honest baselines

Numbers below are measured or stated by others and cited truthfully.

| Baseline | Finding | Source |
|---|---|---|
| HORIZON | κ = 0.84 judge-human agreement on failure attribution | [docs/27](../../../docs/27-horizon-long-horizon-degradation.md) |
| Claw-Eval | Trajectory-opaque evaluation misses 44% of safety violations | [docs/38](../../../docs/38-claw-eval.md) |
| Hermes Agent | Closed learning loop with SKILL.md extraction; self-eval every 15 tasks | [docs/55](../../../docs/55-hermes-agent-self-improving.md) |
| Autogenesis | Propose → assess → commit → rollback for URI-versioned resources | [docs/36](../../../docs/36-autogenesis-self-evolving-agents.md), [docs/57](../../../docs/57-sea-arxiv-2604-15034.md) |
| SEA survey (2508.07407) | Unified feedback-loop formalism 𝒜* = argmax 𝒪(𝒜; ℐ) | [docs/59](../../../docs/59-sea-arxiv-2508-07407.md) |
| LangSmith / Langfuse / Phoenix | Trace storage; no primitive-level attribution | [docs/66](../../../docs/66-meta-harness-landscape.md) |

## Design targets (hypotheses)

These are **design targets** — falsifiable commitments, not measurements.

- **HIR coverage.** The 12-primitive HIR losslessly represents traces from ≥ 6 frameworks. **Assumption:** the primitives we chose from the corpus are a spanning set.
- **Attribution recall.** HAFC recovers ≥ 80% of domain-expert failure labels on a held-out set from the 10 in-tree MVP projects. **Assumption:** primitive-level attribution is learnable with cross-channel evidence + LLM-judge ensemble, approaching HORIZON's κ = 0.84.
- **Evolution compounding.** Over 30 days unattended, Gnomon-driven patches reduce primitive-attributed failure rate by ≥ 30% without regressing task success. **Assumption:** Hermes's ≥ 30% productivity claim generalises when reward is shared across harnesses.
- **Cross-harness portability.** A resource patch fixing a failure in one framework reduces the same primitive's failure rate in ≥ 2 other frameworks when exported via the bundler. **Assumption:** the everything-claude-code cross-harness pattern ([docs/62](../../../docs/62-everything-claude-code.md)) works beyond skills.
- **Chaos coverage.** After 10 SHP injectors are live, every committed patch has a measurably different attribution profile under perturbation vs. nominal. **Assumption:** chaos separates robust patches from brittle ones.

## Component diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                                Gnomon                                 │
│                                                                      │
│  [Framework adapters] ──► [HIR normaliser] ──► [HIR trace store]     │
│     (Claude Code / LangGraph /                                       │
│      Archon / DeerFlow / MCP)                                        │
│                                    │                                 │
│                                    ▼                                 │
│                      [Harness-Aware Failure Classifier]              │
│                     (primitive · class · quote · repro)              │
│                                    │                                 │
│                     ┌──────────────┼──────────────┐                  │
│                     ▼              ▼              ▼                  │
│             [Evolution Loop]  [SHP Chaos]   [Metrics / Dashboards]   │
│             propose → assess    inject      primitive coverage +     │
│             → commit → rollback faults      pairwise decorrelation   │
│                     │                                                │
│                     ▼                                                │
│             [Cross-Harness Patch Bundle]                             │
│             (Claude Code skill · Cursor rule · LangGraph node)       │
└──────────────────────────────────────────────────────────────────────┘
```

## The ten architectural commitments

1. **HIR schema + adapter contract.** Twelve harness primitives drawn from the corpus; one lossless adapter per framework. See [blocks/01-hir-schema.md](blocks/01-hir-schema.md).
2. **HIR trace store.** Append-only, hash-chained, tenant-isolated trace store. See [blocks/02-trace-store.md](blocks/02-trace-store.md).
3. **Harness-Aware Failure Classifier.** Primitive attribution + cross-channel evidence + mesa-guard. See [blocks/03-hafc.md](blocks/03-hafc.md).
4. **Stochastic Harness Perturbation engine.** Deterministic fault injectors per primitive. See [blocks/04-shp.md](blocks/04-shp.md).
5. **Autogenesis-shaped resource patch protocol.** URI-versioned resources, ancestry chain, gate policy. See [blocks/05-patch-protocol.md](blocks/05-patch-protocol.md).
6. **Evolution loop orchestrator.** Propose / assess / commit / rollback. See [blocks/06-evolution-loop.md](blocks/06-evolution-loop.md).
7. **Replay harness.** Re-runs HIR traces against candidate patches in a sandboxed executor. See [blocks/07-replay.md](blocks/07-replay.md).
8. **Cross-harness patch bundler.** Emits per-framework artifacts from one resource patch. See [blocks/08-bundler.md](blocks/08-bundler.md).
9. **Metrics & decorrelation dashboard.** Primitive coverage + pairwise failure decorrelation. See [blocks/09-metrics.md](blocks/09-metrics.md).
10. **Privacy & audit.** Per-tenant isolation, PII scrub, hash-chained audit. See [blocks/10-privacy-audit.md](blocks/10-privacy-audit.md).

## Data flow for a typical ingest-to-patch cycle

1. A Claude Code session produces a trace export; the Claude Code adapter normalises it into HIR events.
2. HIR normaliser validates the event DAG (hash-linked, monotonic timestamps, closed subagent frames).
3. HIR trace store appends to the tenant's log and emits a hash-chained digest.
4. The HAFC pulls the trace + its Vertex-Eval-style rubric result (if available) and classifies each failure into {primitive, class, quote, repro}.
5. If the attribution touches a known resource (e.g. a skill that was invoked), the evolution loop proposes a patch — a new SKILL.md body, a tightened permission rule, a verifier hook added, a compaction rule adjustment.
6. The replay harness re-executes the trace against the candidate patch in a sandbox; compares attributed-failure volume before/after.
7. The gate accepts the patch iff: (a) attributed-failure-rate-on-primitive drops ≥ θ, (b) Pass^k on the replay set does not regress, (c) no new mesa-flag (reward-hack heuristic) fires, (d) a second-family judge agrees.
8. Committed patches enter the Autogenesis resource store with ancestry; the bundler emits per-framework artefacts; the 72h rollback window watches for regression.
9. SHP continuously injects faults in the sandbox; attribution traces produced under chaos feed HAFC training data.

## Novel contributions

1. **The Harness IR.** First explicit portable schema for agent-harness execution. Adapters ship post-hoc so frameworks don't need to opt in.
2. **Primitive-level failure attribution.** First eval system where "failed" decomposes into "compaction dropped the fact on turn 7" vs "permission denied a legitimate action" vs "plan was stale when executed."
3. **Attribution-as-reward for SEA.** First closed evolution loop whose reward signal is harness-primitive-attribution instead of task-success-proxy — usable across every SEA system in the [docs/60](../../../docs/60-sea-top-github-repos.md) catalogue.
4. **Chaos injection per primitive.** First systematic fault injector for agent harnesses; complements Autogenesis's commit/rollback and Claw-Eval's cross-channel discipline.
5. **Cross-harness patch bundling.** Evolved artefacts from one framework automatically targetable at others, extending the everything-claude-code pattern ([docs/62](../../../docs/62-everything-claude-code.md)) from content bundles to evolved content bundles.

## Non-goals

- **Not a new harness framework.** Gnomon consumes existing frameworks; it does not compete with Archon / LangGraph / Claude Code.
- **Not a training platform.** Gnomon evolves *artefacts* (skills, prompts, rules, memory indexes), not model weights.
- **Not a proprietary IR.** HIR is an open schema; adapters are open-source.
- **Not a replacement for task benchmarks.** Gnomon adds the *why-failed* axis; task benchmarks still answer *did-it-pass*.

## Cross-references

- Research corpus: [docs/66 meta-harness](../../../docs/66-meta-harness-landscape.md), [docs/67 proposal](../../../docs/67-recommended-breakthrough-project.md)
- SEA anchors: [docs/36](../../../docs/36-autogenesis-self-evolving-agents.md), [docs/55](../../../docs/55-hermes-agent-self-improving.md), [docs/56](../../../docs/56-sea-landscape-2026.md)
- Primitive anchors: [docs/01](../../../docs/01-agent-loop-architecture.md), [docs/02](../../../docs/02-subagent-delegation.md), [docs/03](../../../docs/03-plan-mode.md), [docs/04](../../../docs/04-skills.md), [docs/05](../../../docs/05-hooks.md), [docs/06](../../../docs/06-permission-modes.md), [docs/08](../../../docs/08-context-compaction.md), [docs/09](../../../docs/09-memory-files.md), [docs/11](../../../docs/11-verifier-evaluator-loops.md), [docs/12](../../../docs/12-todo-scratchpad-state.md)
- Eval anchors: [docs/21](../../../docs/21-llm-as-judge-trajectory-eval.md), [docs/27](../../../docs/27-horizon-long-horizon-degradation.md), [docs/38](../../../docs/38-claw-eval.md), [docs/49](../../../docs/49-agents-of-chaos-red-teaming.md), [docs/53](../../../docs/53-chaos-engineering-next-era.md)
- In-tree precedents: [Vertex-Eval](../../vertex-eval/docs/architecture.md) (ships the evaluator scaffold this project extends), [Cipher-Sec audit](../../cipher-sec/docs/blocks/09-audit-log.md), [Quanta-Proof mesa-guard](../../quanta-proof/src/quanta_proof/gate.py)

## Trade-offs

See [architecture-tradeoff.md](architecture-tradeoff.md).

## Operations

See [system-design.md](system-design.md).

## Status

Design specification + walking-skeleton MVP, April 2026. The MVP implements adapters for one framework (native JSONL), HAFC with three failure classes, SHP with two injectors, evolution loop with one resource type (skill), replay with deterministic seeded execution, bundler with one export format, and FastAPI HTTP surface.
