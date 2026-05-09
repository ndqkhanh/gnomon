"""Gnomon MCP server stub.

Exposes the attribution / classification / patch primitives as MCP
tools for cross-harness consumption.

Tools published:

- ``gnomon.attribute(trace, intended_outcome)`` — primary attribution.
- ``gnomon.classify(attribution)`` — failure-class assignment.
- ``gnomon.propose_patch(attribution, classification)`` — reversible
  patch proposal.
- ``gnomon.bundle(...)`` — cross-harness bundle.
- ``gnomon.health()`` — adapter health.
"""
from __future__ import annotations

import json
import sys
from typing import Any


_PRIMITIVES = (
    "prompt", "tool_call", "tool_result", "context_compact",
    "permission_check", "hook_invocation", "subagent_spawn",
    "memory_read", "memory_write", "skill_load", "verifier_run",
    "commit",
)


def _stub_attribute(trace: list[dict[str, Any]], intended: str) -> dict[str, Any]:
    if not trace:
        return {"primitive": "prompt", "step_idx": 0, "confidence": 0.0,
                "failure_class": "unknown"}
    last = trace[-1]
    prim = last.get("primitive", "tool_call")
    return {
        "primitive": prim if prim in _PRIMITIVES else "tool_call",
        "step_idx": len(trace) - 1,
        "evidence_span": [max(0, len(trace) - 3), len(trace) - 1],
        "confidence": 0.7,
        "failure_class": _stub_class(prim),
    }


def _stub_class(primitive: str) -> str:
    return {
        "context_compact": "compaction_loss",
        "permission_check": "mis_permissioned",
        "skill_load": "skill_miss",
    }.get(primitive, "unknown")


def main() -> int:
    line = sys.stdin.readline()
    if not line.strip():
        print(json.dumps({"error": "no input"}))
        return 0
    req = json.loads(line)
    tool = req.get("tool", "gnomon.attribute")
    args = req.get("args") or {}
    if tool == "gnomon.attribute":
        out = _stub_attribute(args.get("trace") or [], args.get("intended_outcome", ""))
        print(json.dumps({"tool": tool, "result": out}))
    elif tool == "gnomon.classify":
        prim = (args.get("attribution") or {}).get("primitive", "")
        print(json.dumps({"tool": tool, "result": {"failure_class": _stub_class(prim)}}))
    elif tool == "gnomon.propose_patch":
        print(json.dumps({"tool": tool, "result": {
            "diff": "stub-patch",
            "inverse_diff": "stub-revert",
            "expected_lift": 0.0,
        }}))
    elif tool == "gnomon.health":
        print(json.dumps({"tool": tool, "result": {"ok": True}}))
    else:
        print(json.dumps({"tool": tool, "error": f"unknown tool {tool}"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
