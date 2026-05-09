"""Operator-facing metrics — primitive coverage, attribution volume, decorrelation."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

from .models import (
    AttributionReport,
    HIRPrimitive,
    PatchStatus,
    ResourcePatch,
)


@dataclass
class EvolutionStats:
    proposed: int
    committed: int
    rolled_back: int
    rejected: int


def primitive_coverage(reports: Iterable[AttributionReport]) -> Dict[HIRPrimitive, int]:
    """Count attributions per primitive across a set of reports."""
    out: Counter = Counter()
    for r in reports:
        for a in r.attributions:
            out[a.primitive] += 1
    return dict(out)


def attribution_volume(reports: Iterable[AttributionReport], primitive: HIRPrimitive) -> int:
    return sum(
        1
        for r in reports
        for a in r.attributions
        if a.primitive == primitive
    )


def evolution_stats(patches: Iterable[ResourcePatch]) -> EvolutionStats:
    counter: Counter = Counter(p.status for p in patches)
    return EvolutionStats(
        proposed=counter.get(PatchStatus.PROPOSED, 0),
        committed=counter.get(PatchStatus.COMMITTED, 0),
        rolled_back=counter.get(PatchStatus.ROLLED_BACK, 0),
        rejected=counter.get(PatchStatus.REJECTED, 0),
    )


def pairwise_decorrelation(
    runs_by_instance: Mapping[str, Sequence[bool]]
) -> Dict[str, float]:
    """1 - P(both fail | A fails) for each pair of instances.

    Reused unchanged from the Vertex-Eval sla module — shared reliability signal.
    """
    ids = sorted(runs_by_instance.keys())
    out: Dict[str, float] = {}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            ra = list(runs_by_instance[a])
            rb = list(runs_by_instance[b])
            n = min(len(ra), len(rb))
            if n == 0:
                out[f"{a}|{b}"] = 1.0
                continue
            a_fail = sum(1 for k in range(n) if not ra[k])
            both_fail = sum(1 for k in range(n) if not ra[k] and not rb[k])
            if a_fail == 0:
                out[f"{a}|{b}"] = 1.0
            else:
                out[f"{a}|{b}"] = 1.0 - (both_fail / a_fail)
    return out
