import pytest

from gnomon import shp
from gnomon.models import HIRPrimitive


def test_tool_use_latency_spike_increases_latency(happy_trace):
    out = shp.inject(happy_trace, "tool_use.latency_spike", seed=42)
    tool_events = [e for e in out.events if e.primitive == HIRPrimitive.TOOL_USE]
    original = [e for e in happy_trace.events if e.primitive == HIRPrimitive.TOOL_USE]
    assert len(tool_events) == len(original)
    for o, n in zip(original, tool_events):
        assert n.latency_ms > o.latency_ms
        assert n.native_frame["shp_injected"] == "tool_use.latency_spike"


def test_memory_read_stale_fact_marks_stale(compaction_loss_trace):
    # Build a trace with a successful memory_read first, since the compaction
    # fixture marks hit=False.
    from gnomon import hir
    from gnomon.models import HIRPrimitive, HIRTrace

    ev = hir.make_event(
        run_id="r",
        tenant="acme",
        primitive=HIRPrimitive.MEMORY_READ,
        index=0,
        ts_ms=0,
        inputs={"key": "project_root"},
        outputs={"hit": True, "value": "/workspace/repo"},
    )
    chained = hir.chain_events([ev])
    trace = hir.make_trace("t_memhit", "acme", chained)

    out = shp.inject(trace, "memory_read.stale_fact", seed=7)
    mem = [e for e in out.events if e.primitive == HIRPrimitive.MEMORY_READ]
    assert mem
    assert mem[0].outputs["stale"] is True
    assert mem[0].outputs["value"].startswith("[STALE:")


def test_inject_same_seed_same_result(happy_trace):
    a = shp.inject(happy_trace, "tool_use.latency_spike", seed=5)
    b = shp.inject(happy_trace, "tool_use.latency_spike", seed=5)
    # Same seed → identical factor → same latencies
    la = [e.latency_ms for e in a.events]
    lb = [e.latency_ms for e in b.events]
    assert la == lb


def test_inject_unknown_injector_raises():
    import pytest

    from gnomon.models import HIRTrace

    trace = HIRTrace(trace_id="t", tenant="t", events=[])
    with pytest.raises(KeyError):
        shp.inject(trace, "nope", seed=0)


def test_available_and_describe():
    specs = shp.available()
    keys = {s.key for s in specs}
    assert keys == {"tool_use.latency_spike", "memory_read.stale_fact"}
    for k in keys:
        assert shp.describe(k)
