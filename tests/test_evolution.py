from gnomon import evolution, hafc, patches
from gnomon.models import (
    Attribution,
    FailureClass,
    HIRPrimitive,
    PatchClass,
    PatchStatus,
    ResourceScheme,
    ResourceURI,
)


def _skill_miss_attribution():
    return Attribution(
        primitive=HIRPrimitive.SKILL_INVOCATION,
        failure_class=FailureClass.SKILL_MISS,
        event_id="ev_x",
        quote="skill 'weekly_review' failed to match",
        suggested_patch_class=PatchClass.EXTEND_SKILL,
    )


def test_propose_wraps_patch_proposal():
    store = patches.ResourceStore()
    loop = evolution.EvolutionLoop(resource_store=store)
    p = loop.propose(_skill_miss_attribution(), tenant="acme")
    assert p is not None
    assert p.status == PatchStatus.PROPOSED


def test_assess_accepts_patch_that_reduces_attributions(skill_miss_trace):
    store = patches.ResourceStore()
    loop = evolution.EvolutionLoop(resource_store=store)
    p = loop.propose(_skill_miss_attribution(), tenant="acme")
    decision = loop.assess(p, [skill_miss_trace])
    assert decision.accepted is True
    assert decision.attribution_volume_after < decision.attribution_volume_before


def test_assess_rejects_patch_with_no_replay_traces():
    store = patches.ResourceStore()
    loop = evolution.EvolutionLoop(resource_store=store)
    p = loop.propose(_skill_miss_attribution(), tenant="acme")
    decision = loop.assess(p, [])
    assert decision.accepted is False


def test_assess_rejects_patch_that_doesnt_change_attributions(happy_trace):
    """Happy trace has no attributions — any patch cannot REDUCE attributions
    below zero, so the gate must reject (attribution_volume_after >= before)."""
    store = patches.ResourceStore()
    loop = evolution.EvolutionLoop(resource_store=store)
    p = loop.propose(_skill_miss_attribution(), tenant="acme")
    decision = loop.assess(p, [happy_trace])
    assert decision.accepted is False
    assert "attribution volume did not drop" in decision.reason


def test_commit_and_rollback_round_trip():
    store = patches.ResourceStore()
    store.seed(ResourceURI(scheme=ResourceScheme.SKILL, tenant="acme", name="weekly_review"), {"triggers": ["x"]})
    loop = evolution.EvolutionLoop(resource_store=store)
    p = loop.propose(_skill_miss_attribution(), tenant="acme")
    committed = loop.commit(p)
    assert committed.status == PatchStatus.COMMITTED
    rolled = loop.rollback(committed, reason="test")
    assert rolled.status == PatchStatus.ROLLED_BACK


def test_primitive_coverage_guard_blocks_universal_hammer():
    store = patches.ResourceStore()
    # Seed five previously-committed skill patches
    seed_uri = ResourceURI(scheme=ResourceScheme.SKILL, tenant="acme", name="seed")
    committed = []
    for i in range(5):
        uri = ResourceURI(scheme=ResourceScheme.SKILL, tenant="acme", name=f"skill_{i}")
        store.seed(uri, {})
        p = store.propose(uri, diff={"triggers": [f"trig_{i}"]})
        committed.append(store.commit(p.patch_id))

    # New patch would be the 6th consecutive skill-only commit → coverage 6/6 > 0.8
    store.seed(seed_uri, {})
    new_patch = store.propose(seed_uri, diff={"triggers": ["new"]})
    assert evolution.primitive_coverage_ok(committed, new_patch, cap=0.8) is False
