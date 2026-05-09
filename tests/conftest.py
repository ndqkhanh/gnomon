import pytest

from gnomon import hir
from gnomon.models import HIRPrimitive, HIRTrace


def _ev(run_id, tenant, idx, prim, **fields):
    return hir.make_event(
        run_id=run_id,
        tenant=tenant,
        primitive=prim,
        index=idx,
        ts_ms=idx * 10,
        **fields,
    )


@pytest.fixture
def happy_trace() -> HIRTrace:
    run = "run_happy"
    tenant = "acme"
    events = [
        _ev(run, tenant, 0, HIRPrimitive.AGENT_LOOP, inputs={"text": "write config"}),
        _ev(
            run,
            tenant,
            1,
            HIRPrimitive.TOOL_USE,
            inputs={"tool": "Write", "args": {"path": "/workspace/config.json"}},
            outputs={"result": "ok"},
            latency_ms=8,
        ),
        _ev(run, tenant, 2, HIRPrimitive.AGENT_LOOP, outputs={"text": "done"}),
    ]
    events = hir.chain_events(events)
    return hir.make_trace("t_happy", tenant, events, success=True)


@pytest.fixture
def skill_miss_trace() -> HIRTrace:
    run = "run_miss"
    tenant = "acme"
    events = [
        _ev(run, tenant, 0, HIRPrimitive.AGENT_LOOP, inputs={"text": "draft my weekly review"}),
        _ev(
            run,
            tenant,
            1,
            HIRPrimitive.SKILL_INVOCATION,
            inputs={"skill": "weekly_review", "arguments": {"text": "draft my weekly review"}},
            outputs={"matched": False, "result": ""},
        ),
    ]
    events = hir.chain_events(events)
    return hir.make_trace("t_skill_miss", tenant, events, success=False)


@pytest.fixture
def compaction_loss_trace() -> HIRTrace:
    run = "run_compact"
    tenant = "acme"
    events = [
        _ev(
            run,
            tenant,
            0,
            HIRPrimitive.MEMORY_WRITE,
            inputs={"key": "project_root", "value": "/workspace/repo"},
            outputs={"ok": True},
        ),
        _ev(
            run,
            tenant,
            1,
            HIRPrimitive.COMPACTION_EVENT,
            inputs={"trigger": "context_overflow"},
            outputs={"dropped_event_ids": ["ev_project_root_ref"]},
        ),
        _ev(
            run,
            tenant,
            2,
            HIRPrimitive.MEMORY_READ,
            inputs={"key": "project_root"},
            outputs={"hit": False, "value": None},
        ),
    ]
    events = hir.chain_events(events)
    return hir.make_trace("t_compaction", tenant, events, success=False)


@pytest.fixture
def mis_permissioned_trace() -> HIRTrace:
    run = "run_perm"
    tenant = "acme"
    events = [
        _ev(run, tenant, 0, HIRPrimitive.AGENT_LOOP, inputs={"text": "delete tmp file"}),
        _ev(
            run,
            tenant,
            1,
            HIRPrimitive.PERMISSION_CHECK,
            inputs={"action": "Delete", "target": "/tmp/foo"},
            outputs={"decision": "allowed"},
        ),
        _ev(
            run,
            tenant,
            2,
            HIRPrimitive.TOOL_USE,
            inputs={"tool": "Delete", "args": {"path": "/tmp/foo"}},
            outputs={"result": "ok"},
        ),
    ]
    events = hir.chain_events(events)
    return hir.make_trace("t_mis_perm", tenant, events, success=True)
