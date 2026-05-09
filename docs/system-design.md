# Gnomon — System Design

## Runtime topology

```
┌────────────────────────────────────────────────────────────────────┐
│                    Gnomon Control Plane (FastAPI)                  │
│  POST /v1/ingest/native     POST /v1/ingest/claude-code            │
│  POST /v1/attribute         POST /v1/chaos/inject                  │
│  POST /v1/patches/propose   POST /v1/patches/commit                │
│  POST /v1/patches/rollback  POST /v1/bundle                        │
│  GET  /v1/metrics           GET  /healthz                          │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │
   ┌──────────────────────────────┴────────────────────────────────┐
   ▼                                                               ▼
┌───────────────────┐                                    ┌────────────────────┐
│ HIR Trace Store   │ ◄── hash-chained, per-tenant ───► │  Resource Store    │
│  (in-memory MVP;  │                                    │  (URI-versioned    │
│   Postgres later) │                                    │   patches + ancestry)
└─────────┬─────────┘                                    └─────────┬──────────┘
          │                                                        │
          ▼                                                        ▼
   ┌───────────────────────┐                            ┌─────────────────────┐
   │ HAFC Attribution      │                            │ Replay Sandbox       │
   │  (heuristic MVP;      │                            │  (deterministic seed │
   │   LLM-judge roadmap)  │                            │   + synthetic LLM)   │
   └───────────┬───────────┘                            └─────────┬────────────┘
               │                                                  │
               ▼                                                  ▼
        ┌────────────────────────┐                   ┌────────────────────────┐
        │ SHP Chaos Injector     │                   │ Evolution Loop         │
        │  (per-primitive faults)│                   │  (propose → assess     │
        └────────────────────────┘                   │   → commit → rollback) │
                                                     └───────────┬────────────┘
                                                                 ▼
                                                         ┌────────────────┐
                                                         │ Patch Bundler  │
                                                         │ (Claude Code / │
                                                         │  Cursor / ...) │
                                                         └────────────────┘
```

## HTTP surface

### Ingest

- `POST /v1/ingest/native` — body is a HIR-shaped `{trace_id, tenant, events[...]}` object. Validates, appends to store, returns digest.
- `POST /v1/ingest/claude-code` — body is a Claude Code trace export; adapter normalises into HIR.

### Attribution

- `POST /v1/attribute` — body `{trace_id}`. Runs HAFC against stored trace; returns `AttributionReport`.

### Chaos

- `POST /v1/chaos/inject` — body `{trace_id, injector, seed}`. Returns a new trace_id for the perturbed variant.

### Patches

- `POST /v1/patches/propose` — body `{attribution_id}`. Generates a candidate `ResourcePatch`.
- `POST /v1/patches/commit` — body `{patch_id}`. Runs gate; commits or rejects.
- `POST /v1/patches/rollback` — body `{patch_id, reason}`. Reverts.

### Bundle

- `POST /v1/bundle` — body `{patch_id, targets: ["claude-code", "cursor"]}`. Emits per-framework artefacts.

### Metrics

- `GET /v1/metrics` — primitive coverage, attribution volume, pass-rate on replay, decorrelation.

## Storage

| Store | MVP | Production |
|---|---|---|
| HIR traces | in-memory dict + append list | Postgres (JSONB) + object store for large payloads |
| Resource store | in-memory dict | Postgres + Git-backed audit chain |
| Audit log | in-memory list with HMAC | Append-only Postgres + external witness |
| Metrics | in-memory counters | Prometheus + Grafana |

## Security posture

- **Per-tenant isolation** — every trace / patch / audit entry carries tenant; cross-tenant access returns 403.
- **Hash-chained audit** — reused from the Cipher-Sec pattern ([../../cipher-sec/src/cipher_sec/audit.py](../../cipher-sec/src/cipher_sec/audit.py)).
- **PII redactor** — every inbound payload passes through redactor before store (email / phone / card / SSN).
- **Rollback window** — committed patches remain revertable for a configurable window (72h default).
- **Supply-chain discipline** — patch signatures are recommended (HMAC with tenant key) but not required for MVP.

## Deterministic replay

The replay sandbox uses a fixed RNG seed per trace-replay job. The LLM call in replay is faked via a `SyntheticLLM` that returns canned responses keyed on `(trace_id, step_index, tactic)` — this gives reproducible gate decisions. A production deployment can swap in a real LLM; the gate contract is unchanged.

## SLOs (targets, not measurements)

- **Ingest throughput:** 1000 HIR events / s per tenant (MVP); 10000 / s per tenant (prod).
- **Attribution latency:** p95 < 2s per trace on MVP heuristic HAFC; < 30s with LLM judges.
- **Patch commit latency:** p95 < 10s from propose to commit decision (gate-bound).
- **Availability:** 99.5% for MVP single-process; 99.9% with multi-replica.

## Deployment

Docker-first. Single-container by default (`make docker-up`). Docker Compose wires to Postgres + Grafana in a post-MVP `compose.prod.yml` (not shipped in MVP).

## Observability

Every HIR event carries a `run_id`; the audit log hash-chains `(run_id, action, prev_digest)`. FastAPI emits structured JSON logs with `trace_id` + `tenant` on every request. Prometheus histograms on attribution latency, patch-gate decisions, SHP injector outcomes (post-MVP).

## Walking-skeleton scope cap

The MVP ships:

- HIR schema v0.1 with all 12 primitives.
- Adapters: native JSONL, Claude Code trace export.
- HAFC: three failure classes (`compaction_loss`, `mis_permissioned`, `skill_miss`).
- SHP: two injectors (`tool_use.latency_spike`, `memory_read.stale_fact`).
- Evolution loop: one resource type (`skill`), Pass^k-replay gate, mesa-guard.
- Replay harness with SyntheticLLM.
- Bundler: Claude Code SKILL.md output.
- FastAPI with the 10 endpoints above.
- Per-tenant isolation + hash-chained audit + PII redactor.

Post-MVP roadmap (non-goals for this ship):

- LangGraph / Archon / DeerFlow / RAGFlow / LobeHub / OpenClaw adapters.
- LLM-judge HAFC with human-labeled training set.
- 10 additional SHP injectors.
- Evolution on prompt / permission / verifier / memory-index resource types.
- Bundler targets for Cursor / Codex / OpenCode / Antigravity / Gemini.
- Federated LaStraj corpus across tenants (opt-in).
