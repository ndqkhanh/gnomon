"""HIR trace store + hash-chained audit log.

In-memory MVP. The contracts are stable so a Postgres-backed production
replacement can slot in without breaking callers.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from typing import Callable, Dict, List, Optional

from .hir import digest_of, verify_chain
from .models import AuditEntry, HIREvent, HIRTrace


AUDIT_GENESIS = "0" * 64


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


class TraceStore:
    """Append-only, tenant-isolated store for HIR traces."""

    def __init__(self) -> None:
        self._traces: Dict[str, HIRTrace] = {}
        self._by_tenant: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    # --- write paths ---------------------------------------------------

    def put(self, trace: HIRTrace) -> str:
        """Store a trace. Raises on duplicate trace_id or invalid chain."""
        with self._lock:
            if trace.trace_id in self._traces:
                raise ValueError(f"duplicate trace_id: {trace.trace_id}")
            if not verify_chain(trace.events):
                raise ValueError(f"trace {trace.trace_id} has broken hash chain")
            self._traces[trace.trace_id] = trace
            self._by_tenant.setdefault(trace.tenant, []).append(trace.trace_id)
        return self.digest(trace.trace_id)

    def replace(self, trace: HIRTrace) -> str:
        """Idempotent upsert — used by replay/chaos to store perturbed variants."""
        with self._lock:
            if not verify_chain(trace.events):
                raise ValueError(f"trace {trace.trace_id} has broken hash chain")
            self._traces[trace.trace_id] = trace
            if trace.trace_id not in self._by_tenant.setdefault(trace.tenant, []):
                self._by_tenant[trace.tenant].append(trace.trace_id)
        return self.digest(trace.trace_id)

    # --- read paths ----------------------------------------------------

    def get(self, trace_id: str) -> Optional[HIRTrace]:
        return self._traces.get(trace_id)

    def for_tenant(self, tenant: str) -> List[HIRTrace]:
        ids = self._by_tenant.get(tenant, [])
        return [self._traces[i] for i in ids if i in self._traces]

    def digest(self, trace_id: str) -> str:
        trace = self._traces.get(trace_id)
        if trace is None:
            return ""
        if not trace.events:
            return AUDIT_GENESIS
        return digest_of(trace.events[-1])

    def verify(self, trace_id: str) -> bool:
        trace = self._traces.get(trace_id)
        if trace is None:
            return False
        return verify_chain(trace.events)

    def __len__(self) -> int:
        return len(self._traces)

    # --- right-to-erasure ---------------------------------------------

    def redact(self, tenant: str, predicate: Callable[[HIREvent], bool]) -> int:
        """Zero content fields on matching events. Returns count redacted."""
        redacted = 0
        with self._lock:
            for trace_id in self._by_tenant.get(tenant, []):
                trace = self._traces[trace_id]
                new_events: List[HIREvent] = []
                for e in trace.events:
                    if predicate(e):
                        new_events.append(
                            e.model_copy(
                                update={
                                    "inputs": {"__redacted__": True},
                                    "outputs": {"__redacted__": True},
                                    "native_frame": {"__redacted__": True},
                                }
                            )
                        )
                        redacted += 1
                    else:
                        new_events.append(e)
                # re-chain after redaction
                from .hir import chain_events

                new_events = chain_events(new_events)
                self._traces[trace_id] = trace.model_copy(update={"events": new_events})
        return redacted


# =====================================================================
# Audit log — hash-chained, HMAC-signed (pattern from Cipher-Sec)
# =====================================================================


class AuditLog:
    def __init__(self, signing_key: bytes = b"gnomon-dev-only"):
        self._key = signing_key
        self._entries: List[AuditEntry] = []
        self._prev_digest = AUDIT_GENESIS
        self._lock = threading.Lock()

    def append(self, tenant: str, action: str, ref: str = "", actor: str = "gnomon") -> AuditEntry:
        with self._lock:
            entry = AuditEntry(
                index=len(self._entries),
                ts_ms=int(time.time() * 1000),
                tenant=tenant,
                action=action,
                ref=ref,
                actor=actor,
                prev_digest=self._prev_digest,
            )
            payload = entry.model_dump(exclude={"signature"})
            sig = hmac.new(self._key, _canonical(payload).encode(), hashlib.sha256).hexdigest()
            signed = entry.model_copy(update={"signature": sig})
            self._entries.append(signed)
            self._prev_digest = hashlib.sha256(_canonical(signed.model_dump()).encode()).hexdigest()
            return signed

    def __iter__(self):
        return iter(list(self._entries))

    def __len__(self) -> int:
        return len(self._entries)

    def verify(self) -> bool:
        prev = AUDIT_GENESIS
        for e in self._entries:
            payload = e.model_dump(exclude={"signature"})
            expected_sig = hmac.new(self._key, _canonical(payload).encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, e.signature):
                return False
            if e.prev_digest != prev:
                return False
            prev = hashlib.sha256(_canonical(e.model_dump()).encode()).hexdigest()
        return True
