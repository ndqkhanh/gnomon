"""Harness-Aware Failure Classifier — the attribution engine.

MVP ships three heuristic classifiers covering the most common and tractable
classes:
  - ``compaction_loss`` — a ``compaction_event`` dropped an event whose outputs
    were later referenced by a ``memory_read`` that returned empty.
  - ``mis_permissioned`` — a ``permission_check`` with ``decision='denied'``
    followed by retry on a plausibly-legitimate action, OR ``decision='allowed'``
    on a tool-use classified as destructive without a matching HITL approval.
  - ``skill_miss`` — a ``skill_invocation`` returning ``matched=False`` that
    the user then rephrased.

Cross-channel evidence + mesa-guard are applied at the report level.
"""
from __future__ import annotations

from collections import Counter
from typing import List, Optional

from .models import (
    Attribution,
    AttributionReport,
    FailureClass,
    HIREvent,
    HIRPrimitive,
    HIRTrace,
    PatchClass,
)


_DESTRUCTIVE_TOOLS = {"Write", "Edit", "Bash", "Delete", "Exec"}


# ---------------------------------------------------------------------
# Individual classifiers
# ---------------------------------------------------------------------


def _compaction_loss(events: List[HIREvent]) -> List[Attribution]:
    hits: List[Attribution] = []
    dropped_by_event: dict[str, str] = {}
    for e in events:
        if e.primitive == HIRPrimitive.COMPACTION_EVENT:
            for dropped in e.outputs.get("dropped_event_ids", []):
                dropped_by_event[dropped] = e.event_id

    # look for memory reads that returned empty referencing dropped ids
    for e in events:
        if e.primitive == HIRPrimitive.MEMORY_READ and not e.outputs.get("hit", True):
            key = e.inputs.get("key", "")
            for dropped_id, compact_id in dropped_by_event.items():
                if key and key in dropped_id:
                    hits.append(
                        Attribution(
                            primitive=HIRPrimitive.COMPACTION_EVENT,
                            failure_class=FailureClass.COMPACTION_LOSS,
                            event_id=compact_id,
                            quote=f"compaction dropped {dropped_id}; later read missed on key={key!r}",
                            suggested_patch_class=PatchClass.PIN_FACT,
                        )
                    )
    # Fallback: compaction dropped events and subsequent read returned empty
    # (even when key doesn't obviously reference the dropped id).
    if dropped_by_event and not hits:
        for e in events:
            if e.primitive == HIRPrimitive.MEMORY_READ and not e.outputs.get("hit", True):
                # attribute to the most recent compaction event prior to this read
                prior_compact = None
                for x in events:
                    if x.event_id == e.event_id:
                        break
                    if x.primitive == HIRPrimitive.COMPACTION_EVENT:
                        prior_compact = x
                if prior_compact is not None:
                    hits.append(
                        Attribution(
                            primitive=HIRPrimitive.COMPACTION_EVENT,
                            failure_class=FailureClass.COMPACTION_LOSS,
                            event_id=prior_compact.event_id,
                            quote=(
                                f"compaction event {prior_compact.event_id} dropped "
                                f"{len(prior_compact.outputs.get('dropped_event_ids', []))} span(s); "
                                f"subsequent memory_read returned empty"
                            ),
                            confidence=0.6,
                            suggested_patch_class=PatchClass.PIN_FACT,
                        )
                    )
                    break
    return hits


def _mis_permissioned(events: List[HIREvent]) -> List[Attribution]:
    hits: List[Attribution] = []
    for idx, e in enumerate(events):
        if e.primitive != HIRPrimitive.PERMISSION_CHECK:
            continue
        decision = e.outputs.get("decision", "allowed")
        action = e.inputs.get("action", "")
        if decision == "denied":
            # Denied, then the next non-permission event is a retry of same action? → mis-permissioned.
            for later in events[idx + 1 :]:
                if later.primitive == HIRPrimitive.PERMISSION_CHECK and later.inputs.get("action") == action:
                    if later.outputs.get("decision") == "allowed":
                        hits.append(
                            Attribution(
                                primitive=HIRPrimitive.PERMISSION_CHECK,
                                failure_class=FailureClass.MIS_PERMISSIONED,
                                event_id=e.event_id,
                                quote=f"deny on {action!r} later overturned",
                                suggested_patch_class=PatchClass.NARROW_PERMISSION,
                            )
                        )
                    break
                if later.primitive != HIRPrimitive.PERMISSION_CHECK:
                    break
        elif decision == "allowed":
            action_is_destructive = action in _DESTRUCTIVE_TOOLS
            if action_is_destructive:
                # scan for HITL approval hook before or during
                has_hitl = any(
                    x.primitive == HIRPrimitive.HOOK and x.inputs.get("hook") == "hitl_approve"
                    for x in events[: idx + 1]
                )
                if not has_hitl:
                    hits.append(
                        Attribution(
                            primitive=HIRPrimitive.PERMISSION_CHECK,
                            failure_class=FailureClass.MIS_PERMISSIONED,
                            event_id=e.event_id,
                            quote=f"destructive {action!r} allowed without HITL",
                            suggested_patch_class=PatchClass.NARROW_PERMISSION,
                        )
                    )
    return hits


def _skill_miss(events: List[HIREvent]) -> List[Attribution]:
    hits: List[Attribution] = []
    for e in events:
        if e.primitive != HIRPrimitive.SKILL_INVOCATION:
            continue
        if e.outputs.get("matched", True) is False:
            hits.append(
                Attribution(
                    primitive=HIRPrimitive.SKILL_INVOCATION,
                    failure_class=FailureClass.SKILL_MISS,
                    event_id=e.event_id,
                    quote=f"skill {e.inputs.get('skill', '?')!r} failed to match",
                    suggested_patch_class=PatchClass.EXTEND_SKILL,
                )
            )
    return hits


# ---------------------------------------------------------------------
# Cross-channel evidence + mesa-guard
# ---------------------------------------------------------------------


def _apply_cross_channel(trace: HIRTrace, attribution: Attribution) -> Attribution:
    """Mark channels_agree=False when we rely on a single channel only."""
    # MVP heuristic: compaction_loss benefits from an audit + state snapshot, neither of which
    # we currently track — so cap confidence. mis_permissioned has audit-parity via HOOK events.
    if attribution.failure_class == FailureClass.COMPACTION_LOSS:
        has_hook = any(e.primitive == HIRPrimitive.HOOK for e in trace.events)
        if not has_hook:
            return attribution.model_copy(
                update={
                    "channels_agree": False,
                    "confidence": min(attribution.confidence, 0.5),
                }
            )
    return attribution


def _detect_mesa(attributions: List[Attribution]) -> tuple[bool, Optional[str]]:
    """Universal-hammer guard: if a single primitive dominates attributions, flag."""
    if len(attributions) < 4:
        return False, None
    counter = Counter(a.primitive for a in attributions)
    top_primitive, top_count = counter.most_common(1)[0]
    if top_count / len(attributions) >= 0.9:
        return True, f"primitive {top_primitive.value} accounts for {top_count}/{len(attributions)} — universal hammer suspected"
    return False, None


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def classify(trace: HIRTrace) -> AttributionReport:
    events = trace.events
    raw: List[Attribution] = []
    raw.extend(_compaction_loss(events))
    raw.extend(_mis_permissioned(events))
    raw.extend(_skill_miss(events))

    confirmed = [_apply_cross_channel(trace, a) for a in raw]
    cross_ok = all(a.channels_agree for a in confirmed) if confirmed else True
    mesa_flag, mesa_reason = _detect_mesa(confirmed)
    return AttributionReport(
        trace_id=trace.trace_id,
        tenant=trace.tenant,
        attributions=confirmed,
        cross_channel_confirmed=cross_ok,
        mesa_flagged=mesa_flag,
        mesa_reason=mesa_reason,
    )
