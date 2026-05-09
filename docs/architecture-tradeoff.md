# Gnomon — Architecture Trade-offs

## Alternatives considered and rejected

### Alternative A: Build another harness framework (Archon-class)

**Rejected.** [Archon](../../../docs/61-archon-harness-builder.md) and [DeerFlow](../../../docs/65-deer-flow-bytedance.md) already treat the harness as a declarative artefact well. [Deep Agents](../../../docs/42-langchain-deep-agents.md) covers programmatic composition. Adding a 15th framework is crowding, not breakthrough. The 2026 landscape ([docs/66](../../../docs/66-meta-harness-landscape.md)) is starved of *evaluation*, not authoring.

### Alternative B: Another SEA algorithm

**Rejected.** The [2026 SEA survey](../../../docs/59-sea-arxiv-2508-07407.md) and [landscape](../../../docs/56-sea-landscape-2026.md) show algorithms have converged: closed-learning-loop + multi-axis evolution + Autogenesis-shaped patches. The bottleneck is the **shared reward signal**, which Gnomon provides via primitive-level attribution. Another Voyager / Hermes clone without attribution doesn't compound.

### Alternative C: Pure evaluation (Vertex-Eval-only)

**Rejected.** The in-tree [Vertex-Eval](../../vertex-eval/docs/architecture.md) MVP already ships cross-channel evidence + Pass^k SLA + HORIZON-style attribution at the rubric level. Adding the harness-primitive dimension *and* the evolution loop is the breakthrough. Evaluation without action loops creates a dashboard product; action loops without evaluation create uncontrolled self-modification. Both are insufficient alone.

### Alternative D: Chaos-only substrate

**Rejected.** SHP alone is useful (fuzzing for agents) but isolated. Without HAFC to classify what the chaos breaks, it's a testing utility. Without the evolution loop to act on findings, it produces reports not improvements. Three-legged design is required.

### Alternative E: A new Harness IR standard with spec-body only

**Rejected.** History: no schema standard adopts without "killer tooling." Gnomon bundles the IR with three immediately useful products (attribution, evolution, chaos) so adopting the IR *earns* capability the host framework doesn't ship. An IR-only project competes with OpenTelemetry (trace) and CloudEvents (event shape) — both already exist at the generic-events layer.

## Choices made, with reasons

### Choice 1: HIR as a post-hoc conversion target, not an authoring language

**Why:** Developers won't migrate authoring from LangGraph / Archon / Claude Code to a new IR. But they'll happily export their traces into a new IR if it unlocks attribution + evolution. This is the ONNX pattern — post-hoc interchange wins over authoring unification.

**Cost:** Some framework-specific concepts lose fidelity in normalisation. Mitigation: HIR carries a `native_frame` field with the original event for faithful replay; normalisation is lossy only for *classification*, not for *faithful replay*.

### Choice 2: Twelve primitives, not three, not thirty

**Why:** Fewer primitives compress poorly — "tool_use" ≠ "permission_check"; they have different failure modes and different patch classes. More primitives (e.g. split tool_use by stdlib/MCP/http/subprocess) inflate schema without differentiating attribution.

The twelve came directly from the research corpus's independent landmark files ([01](../../../docs/01-agent-loop-architecture.md)–[12](../../../docs/12-todo-scratchpad-state.md)). If the corpus had converged on different primitives, HIR would reflect that.

**Cost:** Some primitive combinations map unevenly across frameworks. Claude Code's `skill` ≠ LangGraph's `subagent` ≠ CrewAI's `agent`, but the HIR `skill_invocation` primitive subsumes all three with carried metadata. The trade-off is that attribution resolution is lower-bounded by HIR granularity.

### Choice 3: Cross-channel evidence as hard gate, not soft confidence

**Why:** Claw-Eval ([docs/38](../../../docs/38-claw-eval.md)) shows trajectory-opaque eval misses 44% of safety violations. Gnomon inherits Vertex-Eval's discipline: an attribution is **confirmed** only when ≥ 2 of 3 channels (trace / audit / state-snapshot) agree. Single-channel attributions are marked low-confidence and gated out of the evolution loop.

**Cost:** When a framework doesn't ship audit or snapshots, attribution confidence caps at medium. Mitigation: the SHP engine *produces* synthetic snapshots during replay, bootstrapping snapshot coverage.

### Choice 4: Autogenesis shape for patches, not JSON-patch or git-diff alone

**Why:** Autogenesis ([docs/36](../../../docs/36-autogenesis-self-evolving-agents.md), [docs/57](../../../docs/57-sea-arxiv-2604-15034.md)) decouples *what evolves* from *how evolution happens*. A patch is a transaction: {resource_uri, diff, ancestry, gate_policy}. This is strictly richer than a git-diff (ancestry + gate) and strictly richer than JSON-patch (typed resource URI).

**Cost:** Ecosystem needs to learn one more shape. Mitigation: the serialisation is JSON; ancestry is hash chain; gate_policy is a rubric ID — nothing exotic.

### Choice 5: Replay-based evaluation, not live A/B

**Why:** Live A/B on a production harness is high-risk (a bad patch breaks real users). Replay on the HIR trace store is zero-risk and deterministic. The trade-off is replay-only can miss emergent behaviour that requires live context; Gnomon addresses this via SHP (chaos) to force coverage of non-recorded conditions.

**Cost:** Replay can't catch "the patch changes behaviour on prompts we've never seen." Mitigation: the Pass^k-on-holdout requirement in the gate forces the patch to work on traces it wasn't optimised against.

### Choice 6: Primitive coverage as a first-class metric

**Why:** A naive SEA system picks the easiest primitive and optimises it to death (reward hacking). Gnomon's gate requires the patch-distribution to spread across primitives over time — the *universal hammer* mesa pattern (seen in [Quanta-Proof's gate](../../quanta-proof/src/quanta_proof/gate.py)) generalises here.

**Cost:** Occasionally forces Gnomon to accept a less-impactful patch because it covers an under-attended primitive. Acceptable: primitive-diversity is a harness-health indicator, not a per-patch KPI.

### Choice 7: Per-tenant isolation by default

**Why:** Customers won't ship traces to a shared store. Multi-tenant isolation is non-negotiable. The audit log is hash-chained per tenant; patches are committed per tenant; bundler outputs are per tenant.

**Cost:** Cross-tenant learning (the LaStraj federation pattern from [Vertex-Eval](../../vertex-eval/src/vertex_eval/lastraj.py)) requires opt-in anonymization + content-hash dedupe. Shipped as an optional module.

### Choice 8: Walking-skeleton MVP — one framework adapter, three failure classes

**Why:** Per docs/67, the 10-week plan ships narrow-but-complete. We get Claude Code → HIR → HAFC(3 classes) → SHP(2 injectors) → evolution(skill patches) → bundler(Claude Code SKILL.md) working end-to-end before adding a second framework adapter.

**Cost:** Other frameworks (LangGraph, Archon, DeerFlow) wait. Mitigation: the HIR schema is already designed for them; adapters are ~200 LoC each.

## Risks and mitigations

### Risk 1: HAFC is an LLM-judge and inherits judge drift

**Mitigation:** Multi-family judge pool + cross-channel evidence + human calibration loop (same pattern Vertex-Eval ships). Label a 200-trace gold set; regression-test every HAFC version against it.

### Risk 2: Patches can poison a skill library (supply-chain attack)

**Mitigation:** (a) Cipher-Sec scope-authorization primitive adapted — every patch carries a signed artefact linking it to an attribution. (b) Hash-chained audit log. (c) Rollback window — patches are reversible for 72h by default. (d) Second-family judge required for the gate.

### Risk 3: HIR primitives don't cover a future framework concept

**Mitigation:** HIR is versioned. `native_frame` carries the untranslated event for forward-compatibility. A v0.2 adds primitives without breaking v0.1 adapters.

### Risk 4: Mesa-optimisation — patches that only look good on replay

**Mitigation:** (a) Pass^k on a held-out replay set. (b) SHP perturbation — patches that don't generalise under chaos fail. (c) Primitive-coverage requirement prevents single-primitive gaming. (d) Quanta-Proof-style guard for proof-shape patterns generalised to patch-shape patterns.

### Risk 5: Performance — HIR normalisation + attribution adds latency

**Mitigation:** Gnomon is an offline / async / batch evaluator, not an inline middleware. Ingestion latency is not a product KPI; attribution latency is.

## What we're explicitly not committing to in MVP

- **Real-LLM HAFC judges.** MVP ships heuristic classifiers that emit the same shape; real-LLM swap is a one-line change.
- **Federated LaStraj corpus.** Opt-in federation across tenants is a post-MVP module.
- **Six framework adapters.** MVP ships native JSONL + one real framework (Claude Code) adapter. LangGraph / Archon / DeerFlow / RAGFlow / LobeHub / OpenClaw are roadmap.
- **Training dataset for HAFC.** MVP uses rule-based classifiers labeled from the 10 in-tree MVP projects. Real training is post-MVP.

These are carried as scope-reductions, not compromised claims — everything labeled "hypothesis" in [architecture.md](architecture.md) stays a hypothesis.

## Why these trade-offs are correct now

The 2026 landscape has 14+ harness frameworks competing on authoring. It has ~10 SEA systems competing on algorithms with non-comparable rewards. It has ~5 trace-storage products that stop at "trace failed." Gnomon's trade-offs position it at the *intersection* — the smallest opinionated scope that unlocks all three simultaneously. Every alternative considered either over-scopes (becomes yet-another-framework) or under-scopes (becomes yet-another-dashboard).
