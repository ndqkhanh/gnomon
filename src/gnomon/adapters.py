"""Framework → HIR adapters.

MVP ships:
  - ``from_native`` — round-trips a HIR-shaped dict.
  - ``from_claude_code`` — normalises a Claude Code trace export (synthetic shape
    defined here; real Claude Code trace formats are swappable).

Additional adapters (LangGraph, DeerFlow, Archon, RAGFlow, LobeHub, OpenClaw)
live on the roadmap; each is ~200 LoC and maps framework concepts into the
same HIR primitive set.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import hir
from .models import HIREvent, HIRPrimitive, HIRTrace


# ---------------------------------------------------------------------
# Native HIR passthrough
# ---------------------------------------------------------------------


def from_native(payload: Dict[str, Any]) -> HIRTrace:
    """Accept a dict already shaped as HIRTrace."""
    return HIRTrace(**payload)


# ---------------------------------------------------------------------
# Claude Code adapter
# ---------------------------------------------------------------------

# Mapping from Claude Code event types → HIR primitive.
# Trace format here is a simplified post-hoc export: each entry is
# {kind, step_index, inputs?, outputs?, latency_ms?, parent_ref?}.
CC_KIND_TO_PRIMITIVE = {
    "user_message": HIRPrimitive.AGENT_LOOP,
    "assistant_message": HIRPrimitive.AGENT_LOOP,
    "skill_invocation": HIRPrimitive.SKILL_INVOCATION,
    "subagent": HIRPrimitive.SUBAGENT_DELEGATION,
    "plan_mode": HIRPrimitive.PLAN_MODE,
    "hook": HIRPrimitive.HOOK,
    "permission_check": HIRPrimitive.PERMISSION_CHECK,
    "tool": HIRPrimitive.TOOL_USE,
    "tool_use": HIRPrimitive.TOOL_USE,
    "compaction": HIRPrimitive.COMPACTION_EVENT,
    "memory_read": HIRPrimitive.MEMORY_READ,
    "memory_write": HIRPrimitive.MEMORY_WRITE,
    "verifier": HIRPrimitive.VERIFIER_CALL,
    "todo": HIRPrimitive.TODO_SCRATCHPAD,
}


def from_claude_code(payload: Dict[str, Any]) -> HIRTrace:
    """Normalise a Claude Code trace export into HIR.

    Expected payload shape::

        {
          "trace_id": "cc_t_<id>",
          "tenant": "acme",
          "session_id": "run_abc",
          "success": true,
          "entries": [
            {"kind": "user_message", "step_index": 0, "text": "...", "ts_ms": 0},
            {"kind": "tool", "step_index": 1, "tool": "Read", "args": {...},
             "result": "...", "latency_ms": 12},
            ...
          ]
        }
    """
    trace_id = payload["trace_id"]
    tenant = payload["tenant"]
    run_id = payload.get("session_id", trace_id)
    success = bool(payload.get("success", True))

    events: List[HIREvent] = []
    last_id_per_scope: List[str] = []  # simple stack for parent_id resolution

    for idx, entry in enumerate(payload.get("entries", [])):
        kind = entry.get("kind", "")
        primitive = CC_KIND_TO_PRIMITIVE.get(kind)
        if primitive is None:
            # unknown kind → fallback to agent_loop, preserving native frame
            primitive = HIRPrimitive.AGENT_LOOP

        inputs, outputs = _split_inputs_outputs(entry, primitive)
        parent_id = last_id_per_scope[-1] if last_id_per_scope else None

        event = hir.make_event(
            run_id=run_id,
            tenant=tenant,
            primitive=primitive,
            index=idx,
            ts_ms=int(entry.get("ts_ms", idx)),
            parent_id=parent_id,
            inputs=inputs,
            outputs=outputs,
            latency_ms=int(entry.get("latency_ms", 0)),
            cost_tokens=int(entry.get("cost_tokens", 0)),
            native_frame={"cc_kind": kind, "cc_entry": entry},
        )
        events.append(event)

        # Very light subagent scoping: a subagent kind opens a parent scope,
        # the next sibling closes it when parent's run completes.
        if primitive == HIRPrimitive.SUBAGENT_DELEGATION:
            last_id_per_scope.append(event.event_id)
        elif last_id_per_scope and entry.get("close_parent"):
            last_id_per_scope.pop()

    events = hir.chain_events(events)
    return hir.make_trace(trace_id=trace_id, tenant=tenant, events=events, success=success)


def _split_inputs_outputs(entry: Dict[str, Any], primitive: HIRPrimitive) -> tuple[dict, dict]:
    """Map CC entry fields into HIR inputs/outputs buckets per primitive."""
    inputs: Dict[str, Any] = {}
    outputs: Dict[str, Any] = {}

    if primitive == HIRPrimitive.TOOL_USE:
        inputs = {"tool": entry.get("tool", ""), "args": entry.get("args", {})}
        outputs = {"result": entry.get("result", "")}
    elif primitive == HIRPrimitive.SKILL_INVOCATION:
        inputs = {"skill": entry.get("skill", ""), "arguments": entry.get("arguments", {})}
        outputs = {"result": entry.get("result", ""), "matched": entry.get("matched", True)}
    elif primitive == HIRPrimitive.MEMORY_READ:
        inputs = {"key": entry.get("key", "")}
        outputs = {"value": entry.get("value", None), "hit": entry.get("hit", True)}
    elif primitive == HIRPrimitive.MEMORY_WRITE:
        inputs = {"key": entry.get("key", ""), "value": entry.get("value", None)}
        outputs = {"ok": entry.get("ok", True)}
    elif primitive == HIRPrimitive.PERMISSION_CHECK:
        inputs = {"action": entry.get("action", ""), "target": entry.get("target", "")}
        outputs = {"decision": entry.get("decision", "allowed")}
    elif primitive == HIRPrimitive.COMPACTION_EVENT:
        inputs = {"trigger": entry.get("trigger", "context_overflow")}
        outputs = {"dropped_event_ids": entry.get("dropped", [])}
    elif primitive == HIRPrimitive.HOOK:
        inputs = {"hook": entry.get("hook", ""), "stage": entry.get("stage", "pre")}
        outputs = {"result": entry.get("result", "")}
    elif primitive == HIRPrimitive.PLAN_MODE:
        inputs = {"plan": entry.get("plan", "")}
        outputs = {"approved": entry.get("approved", True)}
    elif primitive == HIRPrimitive.VERIFIER_CALL:
        inputs = {"verifier": entry.get("verifier", "")}
        outputs = {"ok": entry.get("ok", True), "detail": entry.get("detail", "")}
    elif primitive == HIRPrimitive.TODO_SCRATCHPAD:
        inputs = {"op": entry.get("op", "update")}
        outputs = {"items": entry.get("items", [])}
    elif primitive == HIRPrimitive.SUBAGENT_DELEGATION:
        inputs = {"subagent": entry.get("subagent", ""), "task": entry.get("task", "")}
        outputs = {"result": entry.get("result", "")}
    else:  # AGENT_LOOP or fallback
        inputs = {"text": entry.get("text", "")}
        outputs = {"text": entry.get("text", "")} if entry.get("role") == "assistant" else {}

    return inputs, outputs
