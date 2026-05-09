from gnomon import patches, replay
from gnomon.models import (
    Attribution,
    FailureClass,
    HIRPrimitive,
    PatchClass,
    ResourceScheme,
)


def test_replay_flips_matched_flag_for_extend_skill(skill_miss_trace):
    store = patches.ResourceStore()
    attr = Attribution(
        primitive=HIRPrimitive.SKILL_INVOCATION,
        failure_class=FailureClass.SKILL_MISS,
        event_id="ev",
        quote="skill 'weekly_review' failed to match",
        suggested_patch_class=PatchClass.EXTEND_SKILL,
    )
    patch = patches.propose_from_attribution(store, attr, tenant="acme")
    result = replay.replay_one(skill_miss_trace, patch)
    # Replay should report no remaining skill_miss attributions.
    remaining_miss = [a for a in result.attributions if a.failure_class == FailureClass.SKILL_MISS]
    assert remaining_miss == []


def test_replay_leaves_unrelated_skills_alone():
    from gnomon import hir
    from gnomon.models import HIRPrimitive, HIRTrace

    # A trace whose skill doesn't match the patch's target → no rewrite
    ev = hir.make_event(
        run_id="r",
        tenant="acme",
        primitive=HIRPrimitive.SKILL_INVOCATION,
        index=0,
        ts_ms=0,
        inputs={"skill": "other_skill", "arguments": {}},
        outputs={"matched": False},
    )
    trace = hir.make_trace("t", "acme", hir.chain_events([ev]), success=False)

    store = patches.ResourceStore()
    attr = Attribution(
        primitive=HIRPrimitive.SKILL_INVOCATION,
        failure_class=FailureClass.SKILL_MISS,
        event_id="ev",
        quote="skill 'weekly_review' failed to match",
        suggested_patch_class=PatchClass.EXTEND_SKILL,
    )
    patch = patches.propose_from_attribution(store, attr, tenant="acme")
    result = replay.replay_one(trace, patch)
    assert any(a.failure_class == FailureClass.SKILL_MISS for a in result.attributions)


def test_replay_result_carries_original_and_replayed_ids(skill_miss_trace):
    store = patches.ResourceStore()
    attr = Attribution(
        primitive=HIRPrimitive.SKILL_INVOCATION,
        failure_class=FailureClass.SKILL_MISS,
        event_id="ev",
        quote="skill 'weekly_review' failed to match",
        suggested_patch_class=PatchClass.EXTEND_SKILL,
    )
    patch = patches.propose_from_attribution(store, attr, tenant="acme")
    result = replay.replay_one(skill_miss_trace, patch)
    assert result.original_trace_id == skill_miss_trace.trace_id
    assert result.replayed_trace_id.startswith(skill_miss_trace.trace_id + "__replay:")


def test_replay_batch_returns_one_result_per_trace(skill_miss_trace, happy_trace):
    store = patches.ResourceStore()
    attr = Attribution(
        primitive=HIRPrimitive.SKILL_INVOCATION,
        failure_class=FailureClass.SKILL_MISS,
        event_id="ev",
        quote="skill 'weekly_review' failed to match",
        suggested_patch_class=PatchClass.EXTEND_SKILL,
    )
    patch = patches.propose_from_attribution(store, attr, tenant="acme")
    results = replay.replay_batch([skill_miss_trace, happy_trace], patch)
    assert len(results) == 2
