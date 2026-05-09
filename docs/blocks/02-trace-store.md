# Block 02 — HIR Trace Store

## Responsibility

Append-only, hash-chained, tenant-isolated storage for HIR events. The store is the source of truth every other block reads from.

## Contract

```python
class TraceStore:
    def append(self, event: HIREvent) -> str         # returns digest
    def get_trace(self, trace_id: str) -> list[HIREvent]
    def for_tenant(self, tenant: str) -> list[str]   # trace_ids
    def verify_chain(self, trace_id: str) -> bool    # integrity check
    def redact(self, tenant: str, predicate) -> int  # for GDPR/right-to-erasure
```

## Why append-only + hash-chained

Reused from the Cipher-Sec audit pattern ([../../../cipher-sec/src/cipher_sec/audit.py](../../../cipher-sec/src/cipher_sec/audit.py)). An auditor can verify a trace was not tampered with without reading its contents — they re-compute the digest chain over the canonical JSON and compare to the stored tail.

## Tenant isolation

Every event carries `tenant`. The store maintains separate per-tenant indices; cross-tenant reads return empty. Patches that reference HIR events from a different tenant fail at commit time.

## Storage lifecycle (MVP vs prod)

| Stage | MVP | Production |
|---|---|---|
| write | in-memory dict with locks | Postgres JSONB table, indexed on `(tenant, trace_id, event_id)` |
| read | O(1) by trace_id | indexed scan |
| audit | in-process HMAC chain | external witness + Merkle tree |
| GDPR | `redact()` zeroes content fields but preserves skeleton | same, with hash chain re-computed and dual-audit trail |

## Integrity failure modes

- **Broken chain** — `verify_chain()` returns False; operator alerted; trace marked quarantined and excluded from attribution.
- **Duplicate event_id** — ingest rejects with 409.
- **Missing parent** — ingest rejects with 400.

## Non-goals for MVP

- Multi-node replication.
- Streaming ingestion (Kafka / pub-sub).
- Trace archival to cold storage.
