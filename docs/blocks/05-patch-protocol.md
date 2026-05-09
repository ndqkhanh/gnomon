# Block 05 — Autogenesis-Shaped Resource Patch Protocol

## Responsibility

Define the on-wire shape for evolved artefacts. Directly inherits from [Autogenesis](../../../../docs/36-autogenesis-self-evolving-agents.md) as deepened in [docs/57](../../../../docs/57-sea-arxiv-2604-15034.md) — every patch is a **transaction**, not a file overwrite.

## Contract

```python
class ResourceURI:
    scheme: Literal["skill", "prompt", "permission", "verifier", "memory_index", "hook"]
    tenant: str
    name: str
    version: int

class ResourcePatch:
    patch_id: str                   # deterministic hash of body + ancestor
    resource_uri: ResourceURI
    diff: dict                      # unified diff for text / JSON-patch for struct
    ancestor_digest: str            # hash of the parent resource version
    gate_policy: GatePolicy
    attribution_source: str         # which attribution prompted this patch
    status: PatchStatus             # proposed | committed | rolled_back | rejected

class GatePolicy:
    evaluator: str                  # rubric id
    accept_threshold: float         # e.g. Pass^3 ≥ 0.85 on replay
    rollback_window_hours: int
    require_mesa_clear: bool
    require_second_family_judge: bool
```

## Lifecycle

```
proposed ── gate pass ──► committed
   │                         │
   │                         └── rollback_window trigger ──► rolled_back
   │
   └── gate fail ──► rejected
```

## Why this shape

Not a git diff — git has no gate or ancestry semantics at the resource level. Not a JSON patch — JSON patch lacks typed resource URIs. Autogenesis shape is strictly richer and serialises cleanly as JSON.

## Resource types (MVP: only `skill`)

In MVP, Gnomon only proposes/commits/rolls-back `skill://` patches. The URI scheme supports all six types listed above; implementing proposal logic for the other five is post-MVP work.

## Why ancestry is non-negotiable

Without `ancestor_digest`, you cannot audit *which patch introduced which regression*. With ancestry, the resource store is a versioned DAG — any regression can be traced to a specific patch that can be reverted without affecting independently committed patches.

## Relation to Cipher-Sec

Patch signatures use the same HMAC pattern as [Cipher-Sec ScopeAuthorizer](../../../cipher-sec/src/cipher_sec/scope.py). A signed patch links the proposing agent + the attribution source + the ancestor digest — three-way binding prevents supply-chain attacks where a malicious patch fakes provenance.
