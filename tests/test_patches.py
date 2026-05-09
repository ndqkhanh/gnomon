import pytest

from gnomon import hafc, patches
from gnomon.models import (
    Attribution,
    FailureClass,
    HIRPrimitive,
    PatchClass,
    PatchStatus,
    ResourceScheme,
    ResourceURI,
)


def _uri(name="demo"):
    return ResourceURI(scheme=ResourceScheme.SKILL, tenant="acme", name=name)


def test_propose_returns_patch_with_computed_id():
    s = patches.ResourceStore()
    p = s.propose(_uri(), diff={"triggers": ["foo"]}, attribution_source="ev_x")
    assert p.patch_id.startswith("patch_")
    assert p.status == PatchStatus.PROPOSED
    assert p.ancestor_digest == "0" * 64  # no prior version


def test_commit_applies_diff_and_increments_version():
    s = patches.ResourceStore()
    uri = _uri()
    s.seed(uri, {"triggers": ["old"], "body": "v1"})
    p = s.propose(uri, diff={"triggers": ["new"]})
    committed = s.commit(p.patch_id)
    assert committed.status == PatchStatus.COMMITTED
    body = s.current_body(uri)
    # diff appended to triggers list
    assert set(body["triggers"]) == {"old", "new"}
    assert body["body"] == "v1"  # preserved


def test_rollback_restores_prior_version():
    s = patches.ResourceStore()
    uri = _uri()
    s.seed(uri, {"triggers": ["old"]})
    p = s.propose(uri, diff={"triggers": ["new"]})
    s.commit(p.patch_id)
    s.rollback(p.patch_id, reason="regression")
    body = s.current_body(uri)
    assert body["triggers"] == ["old"]
    assert s.get(p.patch_id).status == PatchStatus.ROLLED_BACK


def test_commit_twice_rejected():
    s = patches.ResourceStore()
    uri = _uri()
    s.seed(uri, {"triggers": ["x"]})
    p = s.propose(uri, diff={"triggers": ["y"]})
    s.commit(p.patch_id)
    with pytest.raises(ValueError):
        s.commit(p.patch_id)


def test_rollback_without_commit_rejected():
    s = patches.ResourceStore()
    p = s.propose(_uri(), diff={"triggers": ["x"]})
    with pytest.raises(ValueError):
        s.rollback(p.patch_id, reason="invalid")


def test_apply_diff_merges_nested_dicts():
    from gnomon.patches import apply_diff

    body = {"meta": {"owner": "alice", "retries": 2}, "triggers": ["a"]}
    diff = {"meta": {"retries": 5, "added": True}, "triggers": ["b"]}
    out = apply_diff(body, diff)
    assert out["meta"] == {"owner": "alice", "retries": 5, "added": True}
    assert set(out["triggers"]) == {"a", "b"}


def test_propose_from_attribution_handles_extend_skill():
    s = patches.ResourceStore()
    attr = Attribution(
        primitive=HIRPrimitive.SKILL_INVOCATION,
        failure_class=FailureClass.SKILL_MISS,
        event_id="ev_abc",
        quote="skill 'weekly_review' failed to match",
        suggested_patch_class=PatchClass.EXTEND_SKILL,
    )
    p = patches.propose_from_attribution(s, attr, tenant="acme")
    assert p is not None
    assert p.resource_uri.name == "weekly_review"
    assert p.resource_uri.scheme == ResourceScheme.SKILL


def test_propose_from_attribution_skips_unsupported_patch_classes():
    s = patches.ResourceStore()
    attr = Attribution(
        primitive=HIRPrimitive.COMPACTION_EVENT,
        failure_class=FailureClass.COMPACTION_LOSS,
        event_id="ev_abc",
        suggested_patch_class=PatchClass.PIN_FACT,
    )
    p = patches.propose_from_attribution(s, attr, tenant="acme")
    assert p is None


def test_ancestor_digest_advances_after_commit():
    s = patches.ResourceStore()
    uri = _uri()
    s.seed(uri, {"triggers": ["x"]})
    before = s.ancestor_digest(uri)
    p = s.propose(uri, diff={"triggers": ["y"]})
    s.commit(p.patch_id)
    after = s.ancestor_digest(uri)
    assert before != after
