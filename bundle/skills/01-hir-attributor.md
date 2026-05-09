---
name: hir-attributor
description: Attribute a failed trace to one HIR primitive.
---
# HIR Attributor

Take a trace + intended outcome. Walk the trace primitive-by-primitive,
score how strongly each primitive's behavior contributed to the
outcome divergence, return the primary attribution.

**Inputs:** `trace: list[HIRStep]`, `intended_outcome: str`.

**Output:**
```yaml
attribution:
  primitive: context_compact   # one of the 12
  step_idx: 7                  # index into trace
  evidence_span: [3, 7]        # trace indices supporting the attribution
  confidence: 0.83
  failure_class: compaction_loss
```

**Telemetry:** emits `gnomon.attribute.<failure_class>`.
