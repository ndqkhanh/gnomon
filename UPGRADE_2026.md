# Gnomon — May-2026 Upgrade Stub

> Companion to [`../CROSS_PROJECT_UPGRADE_PLAN_2026.md`](../CROSS_PROJECT_UPGRADE_PLAN_2026.md).
> Per the cross-project matrix, Gnomon is **W1** — failure attribution
> benefits *every* later install, so ship early.

## Headline gap (vs 2026 SOTA)

- **No `bundle/`** — the 12-primitive HIR + HAFC failure attributor
  + Autogenesis patch proposer not packaged.
- **HIR primitive set not Lyra-routable** — Lyra's L311-1 Agent Teams
  runtime would benefit from Gnomon's failure-attribution as a
  `team.task_failed` post-hook.
- **Cross-harness portability** — HIR is designed to bundle across
  ≥6 frameworks; without the export pipeline, the cross-harness
  artefact bundling stays theoretical.

## Smallest upgrade

```text
gnomon/bundle/
├── bundle.yaml
├── persona.md
├── skills/
│   ├── 01-hir-attributor.md
│   ├── 02-failure-classifier.md
│   ├── 03-autogenesis-patch-proposer.md
│   └── 04-cross-harness-bundler.md
├── tools/
│   └── mcp_server.py          # exposes attributor + classifier + patcher
├── memory/
│   └── seed.md                # 12-primitive IR + 3 known failure classes
├── evals/
│   ├── golden.jsonl           # compaction_loss / mis_permissioned / skill_miss
│   └── rubric.md
└── verifier/
    └── checker.py             # primitive-level attribution recall test
```

## Lyra integration (post-hook)

Once installed, Gnomon's MCP server is wired into Lyra's `LifecycleBus`
as a `team.task_failed` and `tool_call` post-subscriber:

```python
gnomon_subscriber = lambda payload: gnomon_mcp.attribute(
    primitive=payload["tool"],
    failure=payload.get("error"),
)
lifecycle_bus.subscribe(LifecycleEvent.TOOL_CALL, gnomon_subscriber)
```

This makes every Lyra session that has Gnomon installed produce
primitive-attributed failure data — exactly the doc-67 closed-evolution-loop
claim, but now operational.

## Test plan

- 8+ tests covering bundle validation, three known failure classes,
  attributor recall on a canned trace set, and Autogenesis patch
  proposal end-to-end.

## Sequencing

W1 — early; feeds every later install's failure-attribution signal.

## Related Lyra phases

- L311-1 Agent Teams runtime — `team.task_failed` event Gnomon
  subscribes to.
- L311-4 SourceBundle — bundle contract.
- L311-9 Cross-harness export — Gnomon's HIR is the canonical
  cross-harness artefact format.
