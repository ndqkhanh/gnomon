"""Autogenesis-shaped resource patch store.

Maintains a versioned DAG of resources (MVP: `skill://`). Patches are
transactions: {resource_uri, diff, ancestor_digest, gate_policy}.
"""
from __future__ import annotations

import hashlib
import json
import threading
from typing import Dict, List, Optional

from .models import (
    Attribution,
    GatePolicy,
    PatchClass,
    PatchStatus,
    ResourcePatch,
    ResourceScheme,
    ResourceURI,
)


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _digest(obj) -> str:
    return hashlib.sha256(_canonical(obj).encode()).hexdigest()


def patch_id(resource_uri: ResourceURI, diff: dict, ancestor: str) -> str:
    raw = f"{resource_uri.render()}|{_canonical(diff)}|{ancestor}"
    return "patch_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------
# Resource store
# ---------------------------------------------------------------------


class ResourceStore:
    """Versioned resource DAG with ancestry chain."""

    def __init__(self) -> None:
        # uri.render() → list[(version, body)]
        self._by_name: Dict[str, List[tuple[int, dict]]] = {}
        # patch_id → ResourcePatch
        self._patches: Dict[str, ResourcePatch] = {}
        self._lock = threading.Lock()

    def ancestor_digest(self, resource_uri: ResourceURI) -> str:
        """Digest of the current head of the resource DAG, or genesis if new."""
        key = f"{resource_uri.scheme.value}://{resource_uri.tenant}/{resource_uri.name}"
        versions = self._by_name.get(key, [])
        if not versions:
            return "0" * 64
        _, body = versions[-1]
        return _digest(body)

    def current_body(self, resource_uri: ResourceURI) -> Optional[dict]:
        key = f"{resource_uri.scheme.value}://{resource_uri.tenant}/{resource_uri.name}"
        versions = self._by_name.get(key, [])
        if not versions:
            return None
        return versions[-1][1]

    def seed(self, resource_uri: ResourceURI, body: dict) -> None:
        """Install an initial version (v1) for a resource."""
        key = f"{resource_uri.scheme.value}://{resource_uri.tenant}/{resource_uri.name}"
        with self._lock:
            self._by_name[key] = [(1, dict(body))]

    def propose(
        self,
        resource_uri: ResourceURI,
        diff: dict,
        attribution_source: str = "",
        gate_policy: Optional[GatePolicy] = None,
    ) -> ResourcePatch:
        ancestor = self.ancestor_digest(resource_uri)
        pid = patch_id(resource_uri, diff, ancestor)
        patch = ResourcePatch(
            patch_id=pid,
            resource_uri=resource_uri,
            diff=diff,
            ancestor_digest=ancestor,
            gate_policy=gate_policy or GatePolicy(),
            attribution_source=attribution_source,
            status=PatchStatus.PROPOSED,
        )
        with self._lock:
            self._patches[pid] = patch
        return patch

    def commit(self, patch_id: str) -> ResourcePatch:
        with self._lock:
            patch = self._patches.get(patch_id)
            if patch is None:
                raise KeyError(f"unknown patch_id: {patch_id}")
            if patch.status != PatchStatus.PROPOSED:
                raise ValueError(f"cannot commit patch in status {patch.status}")
            new_body = apply_diff(self.current_body(patch.resource_uri) or {}, patch.diff)
            key = (
                f"{patch.resource_uri.scheme.value}://"
                f"{patch.resource_uri.tenant}/{patch.resource_uri.name}"
            )
            versions = self._by_name.setdefault(key, [])
            new_version = (versions[-1][0] + 1) if versions else 1
            versions.append((new_version, new_body))
            committed = patch.model_copy(update={"status": PatchStatus.COMMITTED})
            self._patches[patch_id] = committed
            return committed

    def rollback(self, patch_id: str, reason: str = "") -> ResourcePatch:
        with self._lock:
            patch = self._patches.get(patch_id)
            if patch is None:
                raise KeyError(f"unknown patch_id: {patch_id}")
            if patch.status != PatchStatus.COMMITTED:
                raise ValueError(f"cannot rollback patch in status {patch.status}")
            # Roll resource DAG back to version before this patch
            key = (
                f"{patch.resource_uri.scheme.value}://"
                f"{patch.resource_uri.tenant}/{patch.resource_uri.name}"
            )
            versions = self._by_name.get(key, [])
            if len(versions) >= 2:
                versions.pop()
            rolled = patch.model_copy(update={"status": PatchStatus.ROLLED_BACK})
            self._patches[patch_id] = rolled
            return rolled

    def reject(self, patch_id: str, reason: str = "") -> ResourcePatch:
        with self._lock:
            patch = self._patches.get(patch_id)
            if patch is None:
                raise KeyError(f"unknown patch_id: {patch_id}")
            rejected = patch.model_copy(update={"status": PatchStatus.REJECTED})
            self._patches[patch_id] = rejected
            return rejected

    def get(self, patch_id: str) -> Optional[ResourcePatch]:
        return self._patches.get(patch_id)

    def __len__(self) -> int:
        return len(self._patches)

    def all_patches(self) -> List[ResourcePatch]:
        return list(self._patches.values())


# ---------------------------------------------------------------------
# Diff application — MVP supports dict-merge diffs for skills
# ---------------------------------------------------------------------


def apply_diff(body: dict, diff: dict) -> dict:
    """Apply a shallow merge diff: keys in ``diff`` overwrite ``body``; lists are
    extended when both sides are lists."""
    out = dict(body)
    for k, v in diff.items():
        if k in out and isinstance(out[k], list) and isinstance(v, list):
            out[k] = list(dict.fromkeys(out[k] + v))
        elif k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = apply_diff(out[k], v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------
# Patch proposal helpers — generate a diff from an attribution
# ---------------------------------------------------------------------


def propose_from_attribution(
    store: ResourceStore, attribution: Attribution, tenant: str
) -> Optional[ResourcePatch]:
    """Given an attribution, construct a reasonable patch proposal.

    MVP supports: extend_skill. Other patch classes return None (log and skip).
    """
    if attribution.suggested_patch_class == PatchClass.EXTEND_SKILL:
        skill_name = (attribution.quote.split("'")[1]
                      if "'" in attribution.quote else "unknown_skill")
        skill_name = skill_name.replace("/", "_")[:60] or "unknown_skill"
        uri = ResourceURI(scheme=ResourceScheme.SKILL, tenant=tenant, name=skill_name)
        diff = {
            "triggers": [attribution.quote[:80]],
            "revision_note": f"extended by gnomon in response to {attribution.failure_class.value}",
        }
        return store.propose(uri, diff, attribution_source=attribution.event_id)
    return None
