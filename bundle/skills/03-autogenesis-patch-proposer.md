---
name: autogenesis-patch-proposer
description: Propose a reversible patch that would have fixed the attributed failure.
---
# Autogenesis Patch Proposer

Take an attribution + classification. Propose the **smallest
reversible patch** to the harness that would have changed the
attributed primitive's behavior such that the failure would not
have occurred.

**Patch surface:**

- Compaction policy (`compaction_loss` → adjust the
  retain-priority rule).
- Permission rule (`mis_permissioned` → tighten/loosen the
  matching rule).
- Skill descriptor (`skill_miss` → rewrite the description so
  Argus's cascade picks it).

**Bright line `LBL-GNOMON-REVERSIBLE`:** every patch ships with its
inverse. Production callers run patch → eval → revert if eval drops.

**Output:**

```yaml
patch:
  primitive: context_compact
  diff: |
    +retain: ['user_request', 'last_tool_result', 'plan']
  inverse_diff: |
    -retain: ['user_request', 'last_tool_result', 'plan']
  expected_lift: 0.18   # estimated pass-rate delta
```
