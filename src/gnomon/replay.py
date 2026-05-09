"""Deterministic replay sandbox.

Re-executes a HIR trace with a candidate patch in place and emits a perturbed
trace for comparison. Uses a canned SyntheticLLM so replays are reproducible.

The MVP 'patch effect' is simple: a skill-extension patch rewrites the matched
flag on `skill_invocation` events whose inputs mention any trigger phrase the
patch added. Other patch types are no-ops in replay for now.
"""
from __future__ import annotations

import time
from typing import List, Optional

from . import hafc, hir
from .models import (
    Attribution,
    HIREvent,
    HIRPrimitive,
    HIRTrace,
    ReplayResult,
    ResourcePatch,
    ResourceScheme,
)


class SyntheticLLM:
    """Deterministic stub — returns canned responses keyed on (event_id, primitive)."""

    def respond(self, event: HIREvent) -> str:
        return f"synthetic-response::{event.event_id}::{event.primitive.value}"


def _apply_patch_to_event(event: HIREvent, patch: ResourcePatch) -> HIREvent:
    """Apply a skill-extension patch to a matching skill_invocation event."""
    if patch.resource_uri.scheme != ResourceScheme.SKILL:
        return event
    if event.primitive != HIRPrimitive.SKILL_INVOCATION:
        return event

    skill_name = event.inputs.get("skill", "")
    # This patch targets a named skill — only rewrite if names match.
    if patch.resource_uri.name != skill_name.replace("/", "_")[:60]:
        return event

    triggers = patch.diff.get("triggers", [])
    if not triggers:
        return event

    # The patch "taught" the skill to match on new phrases — in replay, flip
    # the `matched` flag to True for events that previously failed to match.
    if event.outputs.get("matched", True) is False:
        return event.model_copy(
            update={
                "outputs": {
                    **event.outputs,
                    "matched": True,
                    "result": f"patched: matched via extended triggers",
                },
                "native_frame": {
                    **event.native_frame,
                    "gnomon_replay_patch": patch.patch_id,
                },
            }
        )
    return event


def replay_one(trace: HIRTrace, patch: ResourcePatch) -> ReplayResult:
    start = time.perf_counter()
    new_events: List[HIREvent] = [_apply_patch_to_event(e, patch) for e in trace.events]
    new_events = hir.chain_events(new_events)
    new_id = f"{trace.trace_id}__replay:{patch.patch_id}"
    new_trace = hir.make_trace(
        trace_id=new_id, tenant=trace.tenant, events=new_events, success=trace.success
    )
    report = hafc.classify(new_trace)
    elapsed = int((time.perf_counter() - start) * 1000)
    return ReplayResult(
        original_trace_id=trace.trace_id,
        replayed_trace_id=new_id,
        success=True,
        attributions=report.attributions,
        elapsed_ms=elapsed,
    )


def replay_batch(traces: List[HIRTrace], patch: ResourcePatch) -> List[ReplayResult]:
    return [replay_one(t, patch) for t in traces]
