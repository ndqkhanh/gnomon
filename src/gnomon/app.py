"""FastAPI surface for Gnomon."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import adapters, bundler, evolution, hafc, hir, metrics, patches, replay, shp
from .models import (
    AttributionReport,
    BundleArtefact,
    BundleTarget,
    HIREvent,
    HIRPrimitive,
    HIRTrace,
    ResourcePatch,
    ResourceScheme,
    ResourceURI,
)
from .store import AuditLog, TraceStore


app = FastAPI(title="Gnomon", version="0.1.0")

_store = TraceStore()
_audit = AuditLog()
_resource_store = patches.ResourceStore()
_bundler = bundler.Bundler()
_loop = evolution.EvolutionLoop(resource_store=_resource_store)


# ---------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------


class IngestNativeRequest(BaseModel):
    payload: Dict[str, Any]


class IngestClaudeCodeRequest(BaseModel):
    payload: Dict[str, Any]


class AttributeRequest(BaseModel):
    trace_id: str


class ChaosRequest(BaseModel):
    trace_id: str
    injector: str
    seed: int = 0


class ProposeRequest(BaseModel):
    trace_id: str
    attribution_index: int = 0


class CommitRequest(BaseModel):
    patch_id: str
    replay_trace_ids: List[str] = []


class RollbackRequest(BaseModel):
    patch_id: str
    reason: str = ""


class BundleRequest(BaseModel):
    patch_id: str
    targets: List[BundleTarget] = [BundleTarget.CLAUDE_CODE]


# ---------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "service": "gnomon"}


@app.post("/v1/ingest/native")
def ingest_native(req: IngestNativeRequest) -> dict:
    try:
        trace = adapters.from_native(req.payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        _store.put(trace)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _audit.append(tenant=trace.tenant, action="ingest", ref=trace.trace_id)
    return {"trace_id": trace.trace_id, "digest": _store.digest(trace.trace_id)}


@app.post("/v1/ingest/claude-code")
def ingest_claude_code(req: IngestClaudeCodeRequest) -> dict:
    try:
        trace = adapters.from_claude_code(req.payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        _store.put(trace)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _audit.append(tenant=trace.tenant, action="ingest.claude-code", ref=trace.trace_id)
    return {"trace_id": trace.trace_id, "digest": _store.digest(trace.trace_id)}


# ---------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------


@app.post("/v1/attribute", response_model=AttributionReport)
def attribute(req: AttributeRequest) -> AttributionReport:
    trace = _store.get(req.trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    report = hafc.classify(trace)
    _audit.append(tenant=trace.tenant, action="attribute", ref=req.trace_id)
    return report


# ---------------------------------------------------------------------
# Chaos
# ---------------------------------------------------------------------


@app.get("/v1/chaos/injectors")
def list_injectors() -> dict:
    return {"injectors": [{"key": s.key, "description": s.description} for s in shp.available()]}


@app.post("/v1/chaos/inject")
def chaos_inject(req: ChaosRequest) -> dict:
    trace = _store.get(req.trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    try:
        perturbed = shp.inject(trace, req.injector, req.seed)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _store.replace(perturbed)
    _audit.append(
        tenant=trace.tenant,
        action="chaos.inject",
        ref=f"{perturbed.trace_id}<-{req.injector}(seed={req.seed})",
    )
    return {
        "perturbed_trace_id": perturbed.trace_id,
        "digest": _store.digest(perturbed.trace_id),
    }


# ---------------------------------------------------------------------
# Patches
# ---------------------------------------------------------------------


@app.post("/v1/patches/propose", response_model=ResourcePatch)
def patches_propose(req: ProposeRequest) -> ResourcePatch:
    trace = _store.get(req.trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    report = hafc.classify(trace)
    if req.attribution_index >= len(report.attributions):
        raise HTTPException(status_code=404, detail="attribution_index out of range")
    attribution = report.attributions[req.attribution_index]
    patch = _loop.propose(attribution, tenant=trace.tenant)
    if patch is None:
        raise HTTPException(
            status_code=422,
            detail=f"no MVP proposal available for {attribution.suggested_patch_class}",
        )
    _audit.append(tenant=trace.tenant, action="patch.propose", ref=patch.patch_id)
    return patch


@app.post("/v1/patches/commit")
def patches_commit(req: CommitRequest) -> dict:
    patch = _resource_store.get(req.patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="patch not found")

    # If replay traces are supplied, run the gate; otherwise commit directly (dev mode).
    if req.replay_trace_ids:
        replay_traces = [_store.get(tid) for tid in req.replay_trace_ids]
        missing = [tid for tid, t in zip(req.replay_trace_ids, replay_traces) if t is None]
        if missing:
            raise HTTPException(status_code=404, detail=f"replay traces not found: {missing}")
        decision = _loop.assess(patch, [t for t in replay_traces if t])  # type: ignore[arg-type]
        if not decision.accepted:
            rejected = _loop.reject(patch, reason=decision.reason)
            _audit.append(
                tenant=patch.resource_uri.tenant,
                action="patch.reject",
                ref=patch.patch_id,
            )
            return {"status": rejected.status.value, "reason": decision.reason, "decision": decision.model_dump()}

    committed = _loop.commit(patch)
    _audit.append(tenant=patch.resource_uri.tenant, action="patch.commit", ref=committed.patch_id)
    return {"status": committed.status.value, "patch": committed.model_dump()}


@app.post("/v1/patches/rollback")
def patches_rollback(req: RollbackRequest) -> dict:
    patch = _resource_store.get(req.patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="patch not found")
    try:
        rolled = _loop.rollback(patch, reason=req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _audit.append(
        tenant=patch.resource_uri.tenant,
        action="patch.rollback",
        ref=patch.patch_id,
    )
    return {"status": rolled.status.value}


# ---------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------


@app.post("/v1/bundle", response_model=List[BundleArtefact])
def bundle(req: BundleRequest) -> List[BundleArtefact]:
    patch = _resource_store.get(req.patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="patch not found")
    try:
        artefacts = _bundler.bundle(patch, req.targets)
    except (ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit.append(
        tenant=patch.resource_uri.tenant,
        action="bundle",
        ref=f"{patch.patch_id}->{[t.value for t in req.targets]}",
    )
    return artefacts


# ---------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------


@app.get("/v1/metrics")
def get_metrics(tenant: Optional[str] = None) -> dict:
    reports = []
    traces = _store.for_tenant(tenant) if tenant else [t for t in _store._traces.values()]  # type: ignore[attr-defined]
    for t in traces:
        reports.append(hafc.classify(t))
    cov = {p.value: c for p, c in metrics.primitive_coverage(reports).items()}
    stats = metrics.evolution_stats(_resource_store.all_patches())
    return {
        "traces": len(traces),
        "attribution_reports": len(reports),
        "primitive_coverage": cov,
        "evolution_stats": {
            "proposed": stats.proposed,
            "committed": stats.committed,
            "rolled_back": stats.rolled_back,
            "rejected": stats.rejected,
        },
        "audit_entries": len(_audit),
        "audit_chain_ok": _audit.verify(),
    }
