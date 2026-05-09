from gnomon import hafc
from gnomon.models import FailureClass, HIRPrimitive


def test_happy_trace_produces_no_attributions(happy_trace):
    report = hafc.classify(happy_trace)
    assert report.attributions == []
    assert report.cross_channel_confirmed is True
    assert report.mesa_flagged is False


def test_skill_miss_attributed(skill_miss_trace):
    report = hafc.classify(skill_miss_trace)
    classes = [a.failure_class for a in report.attributions]
    assert FailureClass.SKILL_MISS in classes
    # skill_miss suggests extend_skill patch
    skill_miss = next(a for a in report.attributions if a.failure_class == FailureClass.SKILL_MISS)
    assert skill_miss.suggested_patch_class.value == "extend_skill"


def test_compaction_loss_attributed(compaction_loss_trace):
    report = hafc.classify(compaction_loss_trace)
    classes = [a.failure_class for a in report.attributions]
    assert FailureClass.COMPACTION_LOSS in classes
    # single-channel (no audit HOOK events in this trace) → channels_agree=False
    compaction = next(a for a in report.attributions if a.failure_class == FailureClass.COMPACTION_LOSS)
    assert compaction.channels_agree is False
    assert compaction.confidence <= 0.5


def test_mis_permissioned_destructive_without_hitl(mis_permissioned_trace):
    report = hafc.classify(mis_permissioned_trace)
    classes = [a.failure_class for a in report.attributions]
    assert FailureClass.MIS_PERMISSIONED in classes
    mis = next(a for a in report.attributions if a.failure_class == FailureClass.MIS_PERMISSIONED)
    assert mis.primitive == HIRPrimitive.PERMISSION_CHECK
    assert "Delete" in mis.quote


def test_mesa_guard_fires_on_single_primitive_dominance(skill_miss_trace):
    from gnomon import hir
    from gnomon.models import HIRTrace

    # Build a trace with six skill misses to trip the ≥ 0.9 dominance guard
    events = []
    for i in range(6):
        events.append(
            hir.make_event(
                run_id="dominant",
                tenant="acme",
                primitive=HIRPrimitive.SKILL_INVOCATION,
                index=i,
                ts_ms=i,
                inputs={"skill": f"skill_{i}", "arguments": {}},
                outputs={"matched": False, "result": ""},
            )
        )
    events = hir.chain_events(events)
    trace = hir.make_trace("t_dom", "acme", events, success=False)
    report = hafc.classify(trace)
    assert report.mesa_flagged is True
    assert "universal hammer" in (report.mesa_reason or "")
