---
name: 'recover-from-stale-memory'
description: 'Re-fetch pattern for stale memory reads detected by HIR attribution.'
version: '0.1.0'
triggers: ['stale-memory', 'cache-miss']
tags: ['hir-derived', 'recovery', 'memory']
---

# Goal
Detect and recover from stale memory reads before they propagate into
downstream claims.

# Constraints & Style
- Memory reads carry a `freshness_ttl`; expired entries trigger re-fetch.
- A `Memory.compaction_dropped_fact` HIR event invalidates the affected
  partition; re-fetch from source.

# Workflow
1. Read memory partition with TTL check.
2. On TTL expiry, fetch from canonical source and refresh.
3. On `compaction_dropped_fact` event, invalidate partition and re-fetch.
4. Emit `Memory.refresh.success` HIR event when complete.
