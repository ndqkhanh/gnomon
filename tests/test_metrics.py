from gnomon import hafc, metrics, patches
from gnomon.models import (
    Attribution,
    AttributionReport,
    FailureClass,
    HIRPrimitive,
    PatchClass,
    PatchStatus,
    ResourceScheme,
    ResourceURI,
)


def _attribution(primitive):
    return Attribution(
        primitive=primitive,
        failure_class=FailureClass.SKILL_MISS,
        event_id="ev",
        suggested_patch_class=PatchClass.EXTEND_SKILL,
    )


def test_primitive_coverage_counts_attributions():
    r1 = AttributionReport(trace_id="a", tenant="t", attributions=[_attribution(HIRPrimitive.SKILL_INVOCATION)])
    r2 = AttributionReport(
        trace_id="b",
        tenant="t",
        attributions=[
            _attribution(HIRPrimitive.SKILL_INVOCATION),
            _attribution(HIRPrimitive.COMPACTION_EVENT),
        ],
    )
    cov = metrics.primitive_coverage([r1, r2])
    assert cov[HIRPrimitive.SKILL_INVOCATION] == 2
    assert cov[HIRPrimitive.COMPACTION_EVENT] == 1


def test_attribution_volume_filters_by_primitive():
    r = AttributionReport(
        trace_id="a",
        tenant="t",
        attributions=[
            _attribution(HIRPrimitive.SKILL_INVOCATION),
            _attribution(HIRPrimitive.TOOL_USE),
        ],
    )
    assert metrics.attribution_volume([r], HIRPrimitive.SKILL_INVOCATION) == 1
    assert metrics.attribution_volume([r], HIRPrimitive.TOOL_USE) == 1
    assert metrics.attribution_volume([r], HIRPrimitive.HOOK) == 0


def test_evolution_stats_counts_by_status():
    store = patches.ResourceStore()
    uri = ResourceURI(scheme=ResourceScheme.SKILL, tenant="acme", name="s1")
    store.seed(uri, {})
    p1 = store.propose(uri, diff={"triggers": ["a"]})
    store.commit(p1.patch_id)
    p2 = store.propose(uri, diff={"triggers": ["b"]})
    store.commit(p2.patch_id)
    store.rollback(p2.patch_id)
    p3 = store.propose(uri, diff={"triggers": ["c"]})
    store.reject(p3.patch_id, reason="bad")

    stats = metrics.evolution_stats(store.all_patches())
    assert stats.committed == 1  # p1 still committed; p2 rolled back
    assert stats.rolled_back == 1
    assert stats.rejected == 1


def test_pairwise_decorrelation_orthogonal_is_one():
    runs = {
        "a": [True, False, True, False],
        "b": [False, True, False, True],
    }
    out = metrics.pairwise_decorrelation(runs)
    assert out["a|b"] == 1.0


def test_pairwise_decorrelation_identical_is_zero():
    runs = {"a": [True, False, True, False], "b": [True, False, True, False]}
    out = metrics.pairwise_decorrelation(runs)
    assert out["a|b"] == 0.0
