import pytest

from gnomon.store import AuditLog, TraceStore


def test_put_and_get(happy_trace):
    s = TraceStore()
    digest = s.put(happy_trace)
    assert digest
    assert s.get(happy_trace.trace_id) is happy_trace
    assert s.verify(happy_trace.trace_id) is True


def test_duplicate_trace_rejected(happy_trace):
    s = TraceStore()
    s.put(happy_trace)
    with pytest.raises(ValueError):
        s.put(happy_trace)


def test_tenant_isolation(happy_trace):
    s = TraceStore()
    s.put(happy_trace)
    assert happy_trace in s.for_tenant("acme")
    assert s.for_tenant("other") == []


def test_broken_chain_rejected(happy_trace):
    s = TraceStore()
    # Tamper with one event to break the chain.
    evs = list(happy_trace.events)
    evs[1] = evs[1].model_copy(update={"outputs": {"tampered": True}})
    bad = happy_trace.model_copy(update={"trace_id": "t_bad", "events": evs})
    with pytest.raises(ValueError):
        s.put(bad)


def test_redact_zeroes_matching_events_and_preserves_chain(happy_trace):
    s = TraceStore()
    s.put(happy_trace)
    redacted = s.redact("acme", predicate=lambda e: e.primitive.value == "tool_use")
    assert redacted >= 1
    # chain must still verify after redaction
    assert s.verify(happy_trace.trace_id) is True
    t = s.get(happy_trace.trace_id)
    assert any("__redacted__" in e.inputs for e in t.events)


def test_audit_log_chain_verifies():
    a = AuditLog(signing_key=b"test-key")
    a.append(tenant="t1", action="ingest", ref="trace_1")
    a.append(tenant="t1", action="attribute", ref="trace_1")
    a.append(tenant="t2", action="commit", ref="patch_1")
    assert a.verify() is True
    assert len(a) == 3


def test_audit_log_detects_signature_tamper():
    a = AuditLog(signing_key=b"test-key")
    a.append(tenant="t1", action="ingest", ref="trace_1")
    # Tamper with the internal list (simulate disk corruption).
    tampered = a._entries[0].model_copy(update={"action": "sneaky"})
    a._entries[0] = tampered
    assert a.verify() is False
