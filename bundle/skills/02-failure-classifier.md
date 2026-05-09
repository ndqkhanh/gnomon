---
name: failure-classifier
description: Classify an attributed failure into one of the three known classes.
---
# Failure Classifier

Given an attribution, classify the failure into:

1. `compaction_loss` — context compaction dropped a load-bearing fact.
2. `mis_permissioned` — permission check let the wrong action through
   (or blocked the right one).
3. `skill_miss` — skill loader picked the wrong skill.

When the trace doesn't fit any of the three, classify as `unknown`
and emit a `gnomon.classify.unknown` event so the curator can
consider it for a new class entry.
