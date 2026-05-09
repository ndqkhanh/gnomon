import pytest

from gnomon import bundler, patches
from gnomon.models import (
    BundleTarget,
    PatchStatus,
    ResourceScheme,
    ResourceURI,
)


def test_bundle_rejects_uncommitted_patch():
    store = patches.ResourceStore()
    uri = ResourceURI(scheme=ResourceScheme.SKILL, tenant="acme", name="demo")
    store.seed(uri, {"triggers": []})
    p = store.propose(uri, diff={"triggers": ["x"]})
    b = bundler.Bundler()
    with pytest.raises(ValueError):
        b.bundle(p, [BundleTarget.CLAUDE_CODE])


def test_bundle_emits_claude_code_skill_md():
    store = patches.ResourceStore()
    uri = ResourceURI(scheme=ResourceScheme.SKILL, tenant="acme", name="weekly_review")
    store.seed(uri, {"triggers": []})
    p = store.propose(uri, diff={"triggers": ["draft my weekly review"]})
    committed = store.commit(p.patch_id)
    b = bundler.Bundler()
    artefacts = b.bundle(committed, [BundleTarget.CLAUDE_CODE])
    assert len(artefacts) == 1
    art = artefacts[0]
    assert art.target == BundleTarget.CLAUDE_CODE
    assert art.filename == "weekly_review.md"
    assert "source: gnomon-evolved" in art.content
    assert "draft my weekly review" in art.content
    assert art.checksum


def test_bundle_unsupported_target_raises():
    store = patches.ResourceStore()
    uri = ResourceURI(scheme=ResourceScheme.SKILL, tenant="acme", name="x")
    store.seed(uri, {"triggers": []})
    p = store.propose(uri, diff={"triggers": ["y"]})
    committed = store.commit(p.patch_id)
    b = bundler.Bundler()
    with pytest.raises(NotImplementedError):
        b.bundle(committed, [BundleTarget.CURSOR])


def test_bundle_non_skill_resource_raises():
    store = patches.ResourceStore()
    uri = ResourceURI(scheme=ResourceScheme.PROMPT, tenant="acme", name="planner")
    store.seed(uri, {"body": "old"})
    p = store.propose(uri, diff={"body": "new"})
    committed = store.commit(p.patch_id)
    b = bundler.Bundler()
    with pytest.raises(NotImplementedError):
        b.bundle(committed, [BundleTarget.CLAUDE_CODE])
