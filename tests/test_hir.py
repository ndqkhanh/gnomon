import pytest

from gnomon import hir
from gnomon.models import HIRPrimitive


def test_event_id_is_deterministic_for_same_inputs():
    a = hir.make_event(run_id="r", tenant="t", primitive=HIRPrimitive.AGENT_LOOP, index=0, ts_ms=10)
    b = hir.make_event(run_id="r", tenant="t", primitive=HIRPrimitive.AGENT_LOOP, index=0, ts_ms=999)
    assert a.event_id == b.event_id  # event_id is a function of (run_id, index, primitive)


def test_chain_events_produces_verifiable_chain():
    evs = [
        hir.make_event(run_id="r", tenant="t", primitive=HIRPrimitive.AGENT_LOOP, index=i, ts_ms=i)
        for i in range(5)
    ]
    chained = hir.chain_events(evs)
    assert hir.verify_chain(chained) is True


def test_verify_chain_fails_when_tampered():
    evs = [
        hir.make_event(run_id="r", tenant="t", primitive=HIRPrimitive.AGENT_LOOP, index=i, ts_ms=i)
        for i in range(3)
    ]
    chained = hir.chain_events(evs)
    tampered = list(chained)
    tampered[1] = tampered[1].model_copy(update={"outputs": {"tampered": True}})
    assert hir.verify_chain(tampered) is False


def test_make_trace_rejects_mixed_tenants():
    e1 = hir.make_event(run_id="r", tenant="a", primitive=HIRPrimitive.AGENT_LOOP, index=0)
    e2 = hir.make_event(run_id="r", tenant="b", primitive=HIRPrimitive.AGENT_LOOP, index=1)
    with pytest.raises(ValueError):
        hir.make_trace("t", "a", [e1, e2])


def test_make_trace_rejects_non_monotonic_timestamps():
    e1 = hir.make_event(run_id="r", tenant="t", primitive=HIRPrimitive.AGENT_LOOP, index=0, ts_ms=100)
    e2 = hir.make_event(run_id="r", tenant="t", primitive=HIRPrimitive.AGENT_LOOP, index=1, ts_ms=50)
    with pytest.raises(ValueError):
        hir.make_trace("t", "t", [e1, e2])


def test_make_trace_rejects_unknown_parent_id():
    e1 = hir.make_event(run_id="r", tenant="t", primitive=HIRPrimitive.AGENT_LOOP, index=0)
    e2 = hir.make_event(
        run_id="r",
        tenant="t",
        primitive=HIRPrimitive.TOOL_USE,
        index=1,
        ts_ms=10,
        parent_id="ev_doesnotexist",
    )
    with pytest.raises(ValueError):
        hir.make_trace("t", "t", [e1, e2])


def test_make_trace_accepts_valid_parent_chain():
    e1 = hir.make_event(
        run_id="r", tenant="t", primitive=HIRPrimitive.SUBAGENT_DELEGATION, index=0, ts_ms=0
    )
    e2 = hir.make_event(
        run_id="r",
        tenant="t",
        primitive=HIRPrimitive.TOOL_USE,
        index=1,
        ts_ms=10,
        parent_id=e1.event_id,
    )
    trace = hir.make_trace("t", "t", [e1, e2])
    assert trace.events[1].parent_id == e1.event_id


def test_duplicate_event_id_rejected():
    e = hir.make_event(run_id="r", tenant="t", primitive=HIRPrimitive.AGENT_LOOP, index=0)
    with pytest.raises(ValueError):
        hir.make_trace("t", "t", [e, e])
