"""Pydantic schemas for Gnomon — HIR events, attributions, patches, gates."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# =====================================================================
# HIR primitives — the 12 harness primitives the corpus converged on
# =====================================================================


class HIRPrimitive(str, Enum):
    AGENT_LOOP = "agent_loop"
    SUBAGENT_DELEGATION = "subagent_delegation"
    PLAN_MODE = "plan_mode"
    SKILL_INVOCATION = "skill_invocation"
    HOOK = "hook"
    PERMISSION_CHECK = "permission_check"
    TOOL_USE = "tool_use"
    COMPACTION_EVENT = "compaction_event"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    VERIFIER_CALL = "verifier_call"
    TODO_SCRATCHPAD = "todo_scratchpad"
    EVOLUTION_PATCH = "evolution_patch"


# =====================================================================
# HIR event
# =====================================================================


class HIREvent(BaseModel):
    event_id: str
    run_id: str
    tenant: str
    primitive: HIRPrimitive
    ts_ms: int
    parent_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    cost_tokens: int = 0
    native_frame: Dict[str, Any] = Field(default_factory=dict)
    prev_digest: str = ""


class HIRTrace(BaseModel):
    trace_id: str
    tenant: str
    events: List[HIREvent] = Field(default_factory=list)
    success: bool = True


# =====================================================================
# Attribution — what HAFC emits
# =====================================================================


class FailureClass(str, Enum):
    DROPPED_CONTEXT = "dropped_context"
    STALE_MEMORY = "stale_memory"
    MIS_PERMISSIONED = "mis_permissioned"
    PLAN_BYPASS = "plan_bypass"
    UNVERIFIED_CLAIM = "unverified_claim"
    TOOL_MISUSE = "tool_misuse"
    SKILL_MISS = "skill_miss"
    SUBAGENT_HANDOFF = "subagent_handoff"
    COMPACTION_LOSS = "compaction_loss"
    REWARD_HACK = "reward_hack"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    PROMPT_INJECTION = "prompt_injection"


class PatchClass(str, Enum):
    EXTEND_SKILL = "extend_skill"
    PIN_FACT = "pin_fact"
    NARROW_PERMISSION = "narrow_permission"
    ADD_VERIFIER = "add_verifier"
    REWRITE_PLAN_PROMPT = "rewrite_plan_prompt"
    REINDEX_MEMORY = "reindex_memory"


class Attribution(BaseModel):
    primitive: HIRPrimitive
    failure_class: FailureClass
    event_id: str
    quote: str = ""
    confidence: float = 1.0
    channels_agree: bool = True
    suggested_patch_class: Optional[PatchClass] = None


class AttributionReport(BaseModel):
    trace_id: str
    tenant: str
    attributions: List[Attribution] = Field(default_factory=list)
    cross_channel_confirmed: bool = True
    mesa_flagged: bool = False
    mesa_reason: Optional[str] = None


# =====================================================================
# Resource patches (Autogenesis shape)
# =====================================================================


class ResourceScheme(str, Enum):
    SKILL = "skill"
    PROMPT = "prompt"
    PERMISSION = "permission"
    VERIFIER = "verifier"
    MEMORY_INDEX = "memory_index"
    HOOK = "hook"


class PatchStatus(str, Enum):
    PROPOSED = "proposed"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


class ResourceURI(BaseModel):
    scheme: ResourceScheme
    tenant: str
    name: str
    version: int = 1

    def render(self) -> str:
        return f"{self.scheme.value}://{self.tenant}/{self.name}@v{self.version}"


class GatePolicy(BaseModel):
    evaluator: str = "default_v1"
    accept_threshold: float = 0.85
    rollback_window_hours: int = 72
    require_mesa_clear: bool = True
    require_second_family_judge: bool = True


class ResourcePatch(BaseModel):
    patch_id: str
    resource_uri: ResourceURI
    diff: Dict[str, Any]
    ancestor_digest: str = ""
    gate_policy: GatePolicy = Field(default_factory=GatePolicy)
    attribution_source: str = ""
    status: PatchStatus = PatchStatus.PROPOSED


# =====================================================================
# Gate decision + replay
# =====================================================================


class GateDecision(BaseModel):
    accepted: bool
    reason: str
    pass_pow_k_before: float = 0.0
    pass_pow_k_after: float = 0.0
    attribution_volume_before: int = 0
    attribution_volume_after: int = 0
    mesa_flagged: bool = False


class ReplayResult(BaseModel):
    original_trace_id: str
    replayed_trace_id: str
    success: bool
    attributions: List[Attribution] = Field(default_factory=list)
    elapsed_ms: int = 0


# =====================================================================
# Bundle
# =====================================================================


class BundleTarget(str, Enum):
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    LANGGRAPH = "langgraph"
    OPENCLAW = "openclaw"
    LOBEHUB = "lobehub"


class BundleArtefact(BaseModel):
    target: BundleTarget
    filename: str
    content: str
    checksum: str


# =====================================================================
# Audit
# =====================================================================


class AuditEntry(BaseModel):
    index: int
    ts_ms: int
    tenant: str
    action: str
    ref: str = ""
    actor: str = "gnomon"
    prev_digest: str = ""
    signature: str = ""
