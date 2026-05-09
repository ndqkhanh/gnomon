---
name: cross-harness-bundler
description: Bundle an attribution + patch as a portable artefact for any HIR-compliant harness.
---
# Cross-Harness Bundler

Once a patch lifts pass-rate in the source harness, the
cross-harness bundler emits a portable artefact (HIR-compliant
JSON) that any other HIR-compliant harness can import.

**Bundle shape:**

```json
{
  "hir_version": "1.0",
  "primitive": "context_compact",
  "failure_class": "compaction_loss",
  "patch_diff_json": {...},
  "evidence_traces": [...],
  "tested_in": ["lyra@3.11", "claude-code@2.1.32"],
  "expected_lift": 0.18
}
```

The bundle is sufficient context for another harness to apply the
equivalent patch *without* the source harness's code — just its
HIR-projection.
