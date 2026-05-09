"""harness_core — shared harness primitives for agent systems.

Public API:
    - AgentLoop, LoopResult
    - LLMProvider, MockLLM, AnthropicLLM, get_default_llm
    - Message, ToolCall, ToolResult, StopReason
    - Tool, ToolRegistry, ToolError
    - PermissionMode, PermissionPolicy, PermissionDecision
    - Hook, HookRegistry, HookEvent, HookDecision
    - Memory, MemoryEntry
    - Tracer, Span
"""
from __future__ import annotations

from .hooks import Hook, HookDecision, HookEvent, HookRegistry
from .loop import AgentLoop, LoopResult
from .memory import Memory, MemoryEntry
from .messages import Message, StopReason, ToolCall, ToolResult
from .models import AnthropicLLM, LLMProvider, MockLLM, get_default_llm
from .observability import Span, Tracer
from .permissions import PermissionDecision, PermissionMode, PermissionPolicy
from .tools import Tool, ToolError, ToolRegistry

__all__ = [
    "AgentLoop",
    "AnthropicLLM",
    "Hook",
    "HookDecision",
    "HookEvent",
    "HookRegistry",
    "LLMProvider",
    "LoopResult",
    "Memory",
    "MemoryEntry",
    "Message",
    "MockLLM",
    "PermissionDecision",
    "PermissionMode",
    "PermissionPolicy",
    "Span",
    "StopReason",
    "Tool",
    "ToolCall",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
    "Tracer",
    "get_default_llm",
]
