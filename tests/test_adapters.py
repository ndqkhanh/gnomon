import pytest

from gnomon import adapters, hir
from gnomon.models import HIRPrimitive


def test_from_native_round_trips(happy_trace):
    payload = happy_trace.model_dump()
    t = adapters.from_native(payload)
    assert t.trace_id == happy_trace.trace_id
    assert len(t.events) == len(happy_trace.events)
    assert hir.verify_chain(t.events)


def test_from_claude_code_normalises_entries():
    payload = {
        "trace_id": "cc_t1",
        "tenant": "acme",
        "session_id": "sess_a",
        "success": True,
        "entries": [
            {"kind": "user_message", "text": "hi"},
            {
                "kind": "tool",
                "tool": "Read",
                "args": {"path": "/f"},
                "result": "abc",
                "latency_ms": 12,
            },
            {"kind": "skill_invocation", "skill": "weekly_review", "matched": True},
            {"kind": "permission_check", "action": "Write", "target": "/f", "decision": "allowed"},
        ],
    }
    t = adapters.from_claude_code(payload)
    assert t.trace_id == "cc_t1"
    assert [e.primitive for e in t.events] == [
        HIRPrimitive.AGENT_LOOP,
        HIRPrimitive.TOOL_USE,
        HIRPrimitive.SKILL_INVOCATION,
        HIRPrimitive.PERMISSION_CHECK,
    ]
    assert t.events[1].inputs == {"tool": "Read", "args": {"path": "/f"}}
    assert t.events[1].outputs["result"] == "abc"
    assert hir.verify_chain(t.events)


def test_from_claude_code_falls_back_on_unknown_kind():
    payload = {
        "trace_id": "cc_t2",
        "tenant": "acme",
        "entries": [{"kind": "brand_new_thing", "text": "???"}],
    }
    t = adapters.from_claude_code(payload)
    assert t.events[0].primitive == HIRPrimitive.AGENT_LOOP
    # native frame preserves the original kind
    assert t.events[0].native_frame.get("cc_kind") == "brand_new_thing"


def test_from_claude_code_requires_tenant_and_trace_id():
    with pytest.raises(KeyError):
        adapters.from_claude_code({"trace_id": "x"})
    with pytest.raises(KeyError):
        adapters.from_claude_code({"tenant": "acme"})


def test_from_claude_code_all_primitive_kinds_covered():
    payload = {
        "trace_id": "cc_t3",
        "tenant": "acme",
        "entries": [
            {"kind": kind, "step_index": i}
            for i, kind in enumerate(adapters.CC_KIND_TO_PRIMITIVE)
        ],
    }
    t = adapters.from_claude_code(payload)
    seen = {e.primitive for e in t.events}
    assert len(seen) >= 11  # every distinct primitive in the mapping
