# Block 10 — Privacy & Audit

## Responsibility

Keep Gnomon trustworthy: per-tenant data isolation, PII redaction on ingest, hash-chained append-only audit of every mutating action, and a well-defined right-to-erasure path.

## Per-tenant isolation

Every object carries `tenant`:

- Traces — stored under tenant-keyed indices.
- Patches — resource URIs are scoped by tenant.
- Attributions — always reference the traced tenant.
- Audit entries — per-tenant hash chain.

Cross-tenant reads return empty. Patches that reference resources from a different tenant fail at commit time.

## PII redaction

Reused from [Vertex-Eval `privacy.redact`](../../../vertex-eval/src/vertex_eval/privacy.py). Every ingest passes through the redactor before storage. Redacts:

- email addresses → `[EMAIL]`
- phone numbers → `[PHONE]`
- credit-card-like digit runs → `[CARD]`
- SSN patterns → `[SSN]`

Order of application matters — card / SSN must run before phone to prevent the broader phone regex from swallowing card digit runs.

## Hash-chained audit

Pattern reused from [Cipher-Sec `audit.AuditLog`](../../../cipher-sec/src/cipher_sec/audit.py). Every mutating action (ingest, attribute, propose, commit, rollback) appends:

```python
AuditEntry(
    index: int
    ts_ms: int
    tenant: str
    action: str
    ref: str               # object id
    actor: str
    prev_digest: str
    signature: str         # HMAC(tenant_key, canonical_json(entry))
)
```

`prev_digest` chains entries. An external auditor can verify integrity by re-computing digests over the canonical JSON; no content reading required.

## Right-to-erasure

`TraceStore.redact(tenant, predicate)` zeroes content fields on matching events while preserving the skeleton (event_id, primitive, timestamps). The audit log records an erasure action; the hash chain is re-computed forward from the erased event, with a dual-audit trail linking old and new digests.

## Supply-chain discipline (roadmap)

Patches optionally carry an HMAC signature tying `(patch_id, attribution_source, ancestor_digest)`. A malicious patch with fake ancestry fails signature verification. MVP doesn't require signatures; signed-patch-required mode is a tenant configuration flag for production.

## Non-goals for MVP

- SOC2 evidence-collection automation.
- Key rotation.
- External witness integration for audit chain.
