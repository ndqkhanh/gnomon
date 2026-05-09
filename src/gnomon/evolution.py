"""Evolution loop orchestrator — propose → assess → commit → rollback.

Thin coordinator; heavy lifting lives in patches, replay, hafc modules.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Optional

from . import hafc, patches, replay
from .models import (
    Attribution,
    GateDecision,
    GatePolicy,
    HIRTrace,
    PatchStatus,
    ResourcePatch,
)


@dataclass
class EvolutionLoop:
    resource_store: patches.ResourceStore

    def propose(self, attribution: Attribution, tenant: str) -> Optional[ResourcePatch]:
        return patches.propose_from_attribution(self.resource_store, attribution, tenant)

    # -----------------------------------------------------------------
    # Assessment — run replay, compare attribution volume + pass^k
    # -----------------------------------------------------------------

    def assess(
        self,
        patch: ResourcePatch,
        replay_traces: List[HIRTrace],
    ) -> GateDecision:
        if not replay_traces:
            return GateDecision(
                accepted=False, reason="no replay traces supplied", mesa_flagged=False
            )

        # Baseline attribution volume on the target primitive
        primitive_target = patch.resource_uri.scheme.value
        base_reports = [hafc.classify(t) for t in replay_traces]
        before = _count_attributions(base_reports)
        before_pass = _pass_rate(base_reports)

        # Replay each trace under the patched resource
        replayed = replay.replay_batch(replay_traces, patch)
        after_reports = [_synth_report(t, r) for t, r in zip(replay_traces, replayed)]
        after = _count_attributions(after_reports)
        after_pass = _pass_rate(after_reports)

        mesa_flag = any(r.mesa_flagged for r in base_reports + after_reports)

        policy: GatePolicy = patch.gate_policy
        reasons: List[str] = []
        if after_pass + 1e-9 < before_pass:
            reasons.append(
                f"pass rate regressed: {before_pass:.3f} → {after_pass:.3f}"
            )
        if after >= before:
            reasons.append(
                f"attribution volume did not drop: {before} → {after}"
            )
        if policy.require_mesa_clear and mesa_flag:
            reasons.append("mesa guard fired")

        accepted = not reasons

        return GateDecision(
            accepted=accepted,
            reason="accepted" if accepted else "; ".join(reasons),
            pass_pow_k_before=before_pass,
            pass_pow_k_after=after_pass,
            attribution_volume_before=before,
            attribution_volume_after=after,
            mesa_flagged=mesa_flag,
        )

    # -----------------------------------------------------------------
    # Commit / rollback convenience
    # -----------------------------------------------------------------

    def commit(self, patch: ResourcePatch) -> ResourcePatch:
        return self.resource_store.commit(patch.patch_id)

    def rollback(self, patch: ResourcePatch, reason: str = "") -> ResourcePatch:
        return self.resource_store.rollback(patch.patch_id, reason=reason)

    def reject(self, patch: ResourcePatch, reason: str = "") -> ResourcePatch:
        return self.resource_store.reject(patch.patch_id, reason=reason)


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _count_attributions(reports) -> int:
    return sum(len(r.attributions) for r in reports)


def _pass_rate(reports) -> float:
    if not reports:
        return 0.0
    clean = sum(1 for r in reports if not r.attributions)
    return clean / len(reports)


def _synth_report(original_trace: HIRTrace, replayed: replay.ReplayResult):
    """Synthesise an AttributionReport shape from a ReplayResult for comparison."""
    from .models import AttributionReport

    return AttributionReport(
        trace_id=replayed.replayed_trace_id,
        tenant=original_trace.tenant,
        attributions=replayed.attributions,
    )


# ---------------------------------------------------------------------
# Primitive-coverage guard (universal-hammer prevention over history)
# ---------------------------------------------------------------------


def primitive_coverage_ok(committed: Iterable[ResourcePatch], new_patch: ResourcePatch, cap: float = 0.8) -> bool:
    """Reject patches that would push the committed-distribution past `cap` on one primitive."""
    committed_schemes = [p.resource_uri.scheme for p in committed if p.status == PatchStatus.COMMITTED]
    committed_schemes.append(new_patch.resource_uri.scheme)
    counter = Counter(committed_schemes)
    _, top_count = counter.most_common(1)[0]
    return (top_count / len(committed_schemes)) <= cap
