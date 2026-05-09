"""HIR construction and hash-chain helpers.

The gnomon module's job in this file is deterministic event creation:
given a primitive + inputs + outputs, produce a HIREvent with a stable
event_id and a valid prev_digest linking to its predecessor.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from .models import HIREvent, HIRPrimitive, HIRTrace


GENESIS_DIGEST = "0" * 64


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest_of(event: HIREvent) -> str:
    payload = {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "tenant": event.tenant,
        "primitive": event.primitive.value,
        "ts_ms": event.ts_ms,
        "parent_id": event.parent_id,
        "inputs": event.inputs,
        "outputs": event.outputs,
        "latency_ms": event.latency_ms,
        "cost_tokens": event.cost_tokens,
        "prev_digest": event.prev_digest,
    }
    return hashlib.sha256(_canonical_json(payload).encode()).hexdigest()


def _event_id(run_id: str, index: int, primitive: HIRPrimitive) -> str:
    raw = f"{run_id}:{index}:{primitive.value}"
    return "ev_" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def make_event(
    *,
    run_id: str,
    tenant: str,
    primitive: HIRPrimitive,
    index: int,
    ts_ms: Optional[int] = None,
    parent_id: Optional[str] = None,
    inputs: Optional[Dict[str, Any]] = None,
    outputs: Optional[Dict[str, Any]] = None,
    latency_ms: int = 0,
    cost_tokens: int = 0,
    native_frame: Optional[Dict[str, Any]] = None,
    prev_digest: str = GENESIS_DIGEST,
) -> HIREvent:
    """Build a single HIREvent with deterministic event_id."""
    return HIREvent(
        event_id=_event_id(run_id, index, primitive),
        run_id=run_id,
        tenant=tenant,
        primitive=primitive,
        ts_ms=ts_ms if ts_ms is not None else int(time.time() * 1000),
        parent_id=parent_id,
        inputs=inputs or {},
        outputs=outputs or {},
        latency_ms=latency_ms,
        cost_tokens=cost_tokens,
        native_frame=native_frame or {},
        prev_digest=prev_digest,
    )


def make_trace(trace_id: str, tenant: str, events: List[HIREvent], success: bool = True) -> HIRTrace:
    """Validate basic invariants and return a HIRTrace.

    Invariants (cheap checks — the full verify_chain is in the store):
      - all events share tenant.
      - event_ids are unique.
      - ts_ms is monotonic non-decreasing.
      - parent_id references a prior event or None.
    """
    if any(e.tenant != tenant for e in events):
        raise ValueError("events contain mixed tenants")
    seen_ids = set()
    for e in events:
        if e.event_id in seen_ids:
            raise ValueError(f"duplicate event_id: {e.event_id}")
        seen_ids.add(e.event_id)
    for a, b in zip(events, events[1:]):
        if b.ts_ms < a.ts_ms:
            raise ValueError(f"timestamps not monotonic: {a.ts_ms} -> {b.ts_ms}")
    parents_seen = {None}
    for e in events:
        if e.parent_id is not None and e.parent_id not in parents_seen:
            raise ValueError(f"parent_id {e.parent_id} not seen prior to {e.event_id}")
        parents_seen.add(e.event_id)
    return HIRTrace(trace_id=trace_id, tenant=tenant, events=events, success=success)


def verify_chain(events: List[HIREvent]) -> bool:
    """Return True iff every event's prev_digest matches the digest of its predecessor."""
    prev = GENESIS_DIGEST
    for e in events:
        if e.prev_digest != prev:
            return False
        prev = digest_of(e)
    return True


def chain_events(events: List[HIREvent]) -> List[HIREvent]:
    """Return a new list where each event's prev_digest is recomputed to close the chain."""
    chained: List[HIREvent] = []
    prev = GENESIS_DIGEST
    for e in events:
        new_e = e.model_copy(update={"prev_digest": prev})
        chained.append(new_e)
        prev = digest_of(new_e)
    return chained
