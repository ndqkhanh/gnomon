from fastapi.testclient import TestClient

from gnomon.app import app


client = TestClient(app)


def _skill_miss_payload(trace_id="cc_miss"):
    return {
        "trace_id": trace_id,
        "tenant": "acme",
        "session_id": "sess_1",
        "success": False,
        "entries": [
            {"kind": "user_message", "text": "draft my weekly review"},
            {
                "kind": "skill_invocation",
                "skill": "weekly_review",
                "arguments": {"text": "draft my weekly review"},
                "matched": False,
            },
        ],
    }


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_ingest_claude_code_and_attribute():
    r = client.post("/v1/ingest/claude-code", json={"payload": _skill_miss_payload("cc_attr_1")})
    assert r.status_code == 200
    trace_id = r.json()["trace_id"]
    r2 = client.post("/v1/attribute", json={"trace_id": trace_id})
    assert r2.status_code == 200
    body = r2.json()
    classes = [a["failure_class"] for a in body["attributions"]]
    assert "skill_miss" in classes


def test_duplicate_ingest_409():
    payload = _skill_miss_payload("cc_dup")
    assert client.post("/v1/ingest/claude-code", json={"payload": payload}).status_code == 200
    r = client.post("/v1/ingest/claude-code", json={"payload": payload})
    assert r.status_code == 409


def test_attribute_unknown_trace_404():
    r = client.post("/v1/attribute", json={"trace_id": "nope"})
    assert r.status_code == 404


def test_chaos_injectors_list_and_inject():
    r = client.get("/v1/chaos/injectors")
    assert r.status_code == 200
    assert any(i["key"] == "tool_use.latency_spike" for i in r.json()["injectors"])

    # Ingest a tiny trace with a tool_use
    r2 = client.post(
        "/v1/ingest/claude-code",
        json={
            "payload": {
                "trace_id": "cc_chaos",
                "tenant": "acme",
                "entries": [
                    {"kind": "tool", "tool": "Read", "args": {}, "latency_ms": 10},
                ],
            }
        },
    )
    assert r2.status_code == 200
    r3 = client.post(
        "/v1/chaos/inject",
        json={"trace_id": "cc_chaos", "injector": "tool_use.latency_spike", "seed": 1},
    )
    assert r3.status_code == 200
    assert r3.json()["perturbed_trace_id"].startswith("cc_chaos__shp:")


def test_propose_commit_bundle_full_path():
    # 1) ingest a skill-miss trace
    payload = _skill_miss_payload("cc_full_1")
    assert client.post("/v1/ingest/claude-code", json={"payload": payload}).status_code == 200

    # 2) propose
    rp = client.post("/v1/patches/propose", json={"trace_id": "cc_full_1", "attribution_index": 0})
    assert rp.status_code == 200, rp.text
    patch = rp.json()
    patch_id = patch["patch_id"]

    # 3) commit (no replay — dev mode)
    rc = client.post("/v1/patches/commit", json={"patch_id": patch_id, "replay_trace_ids": []})
    assert rc.status_code == 200, rc.text
    assert rc.json()["status"] == "committed"

    # 4) bundle → claude-code SKILL.md
    rb = client.post("/v1/bundle", json={"patch_id": patch_id, "targets": ["claude-code"]})
    assert rb.status_code == 200, rb.text
    artefacts = rb.json()
    assert len(artefacts) == 1
    assert "source: gnomon-evolved" in artefacts[0]["content"]


def test_propose_commit_with_replay_gate_accepts():
    # Ingest two traces: one fails skill-miss, one succeeds. Gate should accept.
    a = _skill_miss_payload("cc_gate_1")
    client.post("/v1/ingest/claude-code", json={"payload": a})

    # second trace also skill-miss on same skill to feed replay
    b = _skill_miss_payload("cc_gate_2")
    client.post("/v1/ingest/claude-code", json={"payload": b})

    rp = client.post("/v1/patches/propose", json={"trace_id": "cc_gate_1", "attribution_index": 0})
    patch_id = rp.json()["patch_id"]

    rc = client.post(
        "/v1/patches/commit",
        json={"patch_id": patch_id, "replay_trace_ids": ["cc_gate_1", "cc_gate_2"]},
    )
    assert rc.status_code == 200
    assert rc.json()["status"] == "committed"


def test_metrics_endpoint():
    r = client.get("/v1/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "primitive_coverage" in body
    assert "evolution_stats" in body
    assert body["audit_chain_ok"] is True
