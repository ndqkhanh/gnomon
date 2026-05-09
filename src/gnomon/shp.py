"""Stochastic Harness Perturbation — deterministic fault injectors per primitive.

MVP injectors:
  - ``tool_use.latency_spike`` — multiplies tool_use latency by a deterministic factor.
  - ``memory_read.stale_fact`` — replaces memory_read outputs with older value.

Every injector is a pure function of ``(trace, seed)``.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List

from . import hir
from .models import HIREvent, HIRPrimitive, HIRTrace


@dataclass(frozen=True)
class InjectorSpec:
    key: str
    primitive: HIRPrimitive
    description: str


Injector = Callable[[List[HIREvent], random.Random], List[HIREvent]]


def _tool_use_latency_spike(events: List[HIREvent], rng: random.Random) -> List[HIREvent]:
    factor = rng.choice([3, 5, 10, 20])
    out: List[HIREvent] = []
    for e in events:
        if e.primitive == HIRPrimitive.TOOL_USE:
            out.append(
                e.model_copy(
                    update={
                        "latency_ms": e.latency_ms * factor,
                        "native_frame": {
                            **e.native_frame,
                            "shp_injected": "tool_use.latency_spike",
                            "shp_factor": factor,
                        },
                    }
                )
            )
        else:
            out.append(e)
    return out


def _memory_read_stale_fact(events: List[HIREvent], rng: random.Random) -> List[HIREvent]:
    out: List[HIREvent] = []
    swapped = False
    for e in events:
        if e.primitive == HIRPrimitive.MEMORY_READ and e.outputs.get("hit", True):
            staleness = rng.choice(["cached_24h_ago", "cached_48h_ago", "cached_7d_ago"])
            out.append(
                e.model_copy(
                    update={
                        "outputs": {
                            **e.outputs,
                            "value": f"[STALE:{staleness}] {e.outputs.get('value', '')}",
                            "stale": True,
                        },
                        "native_frame": {
                            **e.native_frame,
                            "shp_injected": "memory_read.stale_fact",
                            "shp_staleness": staleness,
                        },
                    }
                )
            )
            swapped = True
        else:
            out.append(e)
    return out


_INJECTORS: Dict[str, Injector] = {
    "tool_use.latency_spike": _tool_use_latency_spike,
    "memory_read.stale_fact": _memory_read_stale_fact,
}

_INJECTOR_SPECS = (
    InjectorSpec(
        key="tool_use.latency_spike",
        primitive=HIRPrimitive.TOOL_USE,
        description="Multiplies tool_use latency by a deterministic factor (3x, 5x, 10x, 20x).",
    ),
    InjectorSpec(
        key="memory_read.stale_fact",
        primitive=HIRPrimitive.MEMORY_READ,
        description="Replaces successful memory_read outputs with content marked stale.",
    ),
)


def available() -> List[InjectorSpec]:
    return list(_INJECTOR_SPECS)


def describe(injector: str) -> str:
    for spec in _INJECTOR_SPECS:
        if spec.key == injector:
            return spec.description
    raise KeyError(f"unknown injector: {injector}")


def inject(trace: HIRTrace, injector: str, seed: int) -> HIRTrace:
    if injector not in _INJECTORS:
        raise KeyError(f"unknown injector: {injector}")
    rng = random.Random(seed)
    perturbed = _INJECTORS[injector](list(trace.events), rng)
    # Re-chain since inputs/outputs changed → digests changed.
    rechained = hir.chain_events(perturbed)
    new_id = f"{trace.trace_id}__shp:{injector}:{seed}"
    return hir.make_trace(
        trace_id=new_id,
        tenant=trace.tenant,
        events=rechained,
        success=trace.success,
    )
