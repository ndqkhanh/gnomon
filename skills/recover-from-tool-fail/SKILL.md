---
name: 'recover-from-tool-fail'
description: 'Retry pattern for primitive-tool failures observed in HIR traces.'
version: '0.1.0'
triggers: ['tool-error', 'retry']
tags: ['hir-derived', 'recovery']
---

# Goal
Recover gracefully from primitive-tool failures.

# Constraints & Style
- Retry up to 3 times with exponential backoff (1s, 2s, 4s).
- Distinguish transient failures (timeout, 5xx) from permanent ones
  (4xx, schema mismatch).
- On permanent failure, escalate to bright-line and pause.

# Workflow
1. Detect the failure signal at the tool boundary.
2. Classify transient vs. permanent.
3. Retry transients with exponential backoff.
4. On persistent failure, surface a structured diagnostic and pause.
