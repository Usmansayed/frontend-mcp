# Async Execution Model — Phase 1 Design

**Date:** 2026-07-13  
**Status:** Phase 1 **implemented** (2026-07-13) — execution tiers + SEO async jobs  
**Parent:** [`ARCHITECTURE_RETHINK.md`](ARCHITECTURE_RETHINK.md)  
**Priority:** **Highest** — biggest current production risk is blocking + sync long-running work

---

## Problem statement

Today the MCP stdio connection is a **single asyncio event loop**. Heavy synchronous work (CRG graph build, file walks, some provider logic) runs inside `async def` handlers without `asyncio.to_thread`. When one tool blocks for seconds or minutes, **all tools hang** — including `perception_health` and `perception_verify`.

SEO audit compounds this: internal pipeline budgets (120–330s) exceed the MCP timeout (90s), and timeout returns an **empty envelope** — wasting orchestrator degradation work.

**Phase 1 goal:** Make the MCP feel instant for Tier A tools while long work runs **off the event loop** in **background jobs** with poll/cancel/progress.

---

## Scope (Phase 1 only)

| In scope | Out of scope (later phases) |
|----------|----------------------------|
| Non-blocking execution runtime | Resolver framework / `resolve_route` |
| Thread/process pool for sync handlers | Removing CRG |
| Job store + SEO `audit_start` / `audit_poll` | Framework docs removal |
| Parallel SEO provider collection | PDG lazy refresh |
| Partial results + evidence cache | Inspiration async jobs |

---

## 1. Execution runtime upgrades

### 1.1 Current state (`src/navigation/execution_runtime/`)

| Component | Exists | Gap |
|-----------|--------|-----|
| `ToolExecutor` + `asyncio.wait_for` timeout | ✅ | Timeout kills handler; no partial result |
| `CancellationToken` | ✅ | Not wired to blocking sync work inside handlers |
| Idempotency + retry + ledger | ✅ | — |
| `asyncio.to_thread` in executor | ❌ | Sync handlers block loop |
| Progress reporting | ❌ | — |
| Job / background task registry | ❌ | — |

### 1.2 Design: execution tiers

```text
Tier SYNC_FAST     handler completes on event loop, <2s guaranteed
Tier SYNC_OFFLOAD  handler body runs in thread pool; awaitable wrapper
Tier BACKGROUND    start returns job_id immediately; work in task/worker
```

**Classification registry** (new: `execution_runtime/policies/tier.py`):

| Tool pattern | Tier |
|--------------|------|
| `perception_health`, `perception_verify`, `perception_flow_describe` | SYNC_FAST |
| `perception_code_context`, CRG, large file walks | SYNC_OFFLOAD (until removed) |
| `perception_seo_audit` (legacy sync) | BACKGROUND → deprecate sync path |
| `perception_seo_audit_start` | BACKGROUND |
| Lighthouse `perception_audit_*` | SYNC_OFFLOAD |
| `perception_navigate_and_observe` | SYNC_FAST (already async browser) |

### 1.3 `run_handler` wrapper (conceptual)

```python
async def run_handler(handler, args, *, tier: ExecutionTier, cancellation: CancellationToken):
    if tier == ExecutionTier.SYNC_FAST:
        return await handler(args)
    if tier == ExecutionTier.SYNC_OFFLOAD:
        return await asyncio.to_thread(_sync_invoke, handler, args, cancellation)
    raise ValueError("BACKGROUND tools must use JobRunner.start(), not run_handler")
```

**Rules:**
- Any handler that calls CRG, subprocess sync, or `Path.rglob` over large trees → **SYNC_OFFLOAD** minimum.
- `ToolExecutor._invoke_handler` routes through `run_handler` based on tier registry.
- Cancellation: pass token into thread work; check between CRG/Lighthouse steps.

### 1.4 Process pool (optional, Phase 1b)

Thread pool sufficient for I/O-bound and GIL-releasing parse work. **Process pool** only if CRG remains temporarily and CPU-bound parse blocks threads.

Default: `ThreadPoolExecutor` with `max_workers` from env `PERCEPTION_EXECUTOR_WORKERS` (default: 4).

### 1.5 Progress reporting (runtime-level)

For SYNC_OFFLOAD and BACKGROUND jobs, expose progress via:

```json
{
  "execution": {
    "execution_id": "ex_...",
    "progress": {
      "phase": "collecting",
      "pct": 42,
      "message": "lighthouse:performance",
      "updated_at": "ISO8601"
    }
  }
}
```

- BACKGROUND: progress updated in job store; poll tool reads it.
- SYNC_OFFLOAD: optional coarse phases for tools >5s (SEO sync fallback only).

### 1.6 Cancellation

| Layer | Behavior |
|-------|----------|
| MCP client disconnect | Set `CancellationToken` on in-flight execution |
| `perception_seo_audit_cancel` | Mark job `cancelled`; providers check flag between steps |
| Thread offload | Cooperative — long loops check token every N iterations |
| Subprocess (Lighthouse) | `proc.terminate()` on cancel |

Wire `CancellationToken` from `ExecutionPolicies` into `JobRunner` and offload wrapper.

### 1.7 Timeout policy changes

| Tool | Current | Proposed |
|------|---------|----------|
| `perception_seo_audit` (sync) | 90s → empty | Deprecate; keep 90s only as legacy with partial job handoff |
| `perception_seo_audit_start` | — | **2s** — must only enqueue |
| `perception_seo_audit_poll` | — | **5s** |
| `perception_code_context` | 30s | SYNC_OFFLOAD; consider fail-fast deprecate |

**On sync timeout for migratable tools:** if work started, return `{ ok: false, error: "timeout", data: { job_id, resume_via: "perception_seo_audit_poll" } }` — never empty `data`.

---

## 2. SEO async job model

### 2.1 New tools

| Tool | Role | Target latency |
|------|------|----------------|
| `perception_seo_audit_start` | Enqueue audit; return `audit_job_id` | **<500ms** |
| `perception_seo_audit_poll` | Status, progress, partial evidence delta | **<200ms** |
| `perception_seo_audit_cancel` | Cancel background job | **<100ms** |
| `perception_seo_audit` | **Legacy** — delegates to start+blocking poll or deprecated | migrate off |

### 2.2 Job state machine

```text
queued → bootstrapping → collecting → analyzing → completed
           │                │              │
           └ degraded       └ partial      └ input_required (OAuth)
failed / cancelled
```

Terminal: `completed`, `failed`, `cancelled`.  
Resumable pause: `input_required` (GSC OAuth).

### 2.3 Job store

**Location:** `.cache/seo_jobs/{audit_job_id}.json` + in-memory index for active jobs.

```json
{
  "audit_job_id": "audit_abc123",
  "status": "collecting",
  "created_at": 1710000000,
  "updated_at": 1710000042,
  "request": { "website_url": "...", "mode": "development", "scan_id": "..." },
  "progress": {
    "pct": 35,
    "current_provider": "lighthouse",
    "completed_providers": ["browser"],
    "pending_providers": ["librecrawl", "lighthouse"]
  },
  "evidence_ids": ["ev_001", "ev_002"],
  "degraded": ["companion_warm"],
  "error": null,
  "latest_audit_id": null
}
```

On `completed`, merge into existing `SeoKnowledgeGraphStore` — reuse `audit_id` for `seo_query` / `seo_verify`.

### 2.4 Background worker

```text
seo_audit_start
  → JobStore.create()
  → asyncio.create_task(_run_audit_job(job_id))  # does NOT block stdio return
  → return { audit_job_id, poll_interval_ms: 2000 }

_run_audit_job:
  → ensure_companions (with cancel checks)
  → asyncio.gather(collect providers, return_exceptions=True)  # PARALLEL
  → append evidence to job + graph incrementally after each provider
  → ai_visibility when evidence threshold met
  → recommendations
  → status = completed
```

**Critical:** Provider collection **parallel**, not sequential (`orchestrator.py` today).

### 2.5 Poll response envelope

```json
{
  "ok": true,
  "data": {
    "audit_job_id": "audit_abc123",
    "status": "collecting",
    "terminal": false,
    "progress": { "pct": 35, "current_provider": "lighthouse" },
    "evidence_delta": [ { "evidence_id": "ev_002", "kind": "technical_issue", "summary": "..." } ],
    "evidence_count": 12,
    "degraded": ["lighthouse_pending"],
    "partial_summary": { "critical_issues": 1 },
    "poll_interval_ms": 2000,
    "latest_audit_id": null
  }
}
```

`evidence_delta`: only evidence added since `since_evidence_id` or `since_poll_seq` param — keeps polls small.

### 2.6 Caching strategy

| Cache | Key | TTL | Use |
|-------|-----|-----|-----|
| Lighthouse LHR | `url` + category + session | 1h | Skip re-run if fresh |
| Browser evidence | `scan_id` + url | session | Instant on poll |
| LibreCrawl crawl | `website_url` + crawl_id | 24h | Reuse sitemap pages |
| GSC/GA4 API | property + date range | 15–60 min | Professional mode |
| Graph | `SeoKnowledgeGraphStore` | persistent | `seo_query` |

Cache check **before** spawning provider work in job runner.

### 2.7 `seo_verify` migration

**Do not** re-run full audit in verify.  
`seo_verify({ website_url, audit_id, recommendation_ids })` → diff recommendations vs current graph / targeted re-check only.

Full re-audit = explicit `seo_audit_start`.

### 2.8 MCP Tasks alignment

When Cursor supports [MCP Tasks](https://modelcontextprotocol.io/extensions/tasks/overview), map:

- `seo_audit_start` → `resultType: "task"` with `taskId == audit_job_id`
- `seo_audit_poll` → `tasks/get`

Until then, tool-native poll is sufficient.

---

## 3. Implementation checklist (Phase 1)

### 3.1 Execution runtime

- [ ] `ExecutionTier` registry per tool name
- [ ] `run_handler` with `asyncio.to_thread` for SYNC_OFFLOAD
- [ ] Wire `CancellationToken` into offload + job runner
- [ ] Progress field on `ExecutionMetadata` for long sync tools
- [ ] Timeout partial handoff (job_id in `data` on timeout)
- [ ] Tests: health/verify respond while CRG runs in background thread

### 3.2 SEO jobs

- [ ] `JobStore` + `AuditJobRunner`
- [ ] `perception_seo_audit_start` / `_poll` / `_cancel` handlers + MCP schemas
- [ ] Parallel `asyncio.gather` in orchestrator job path
- [ ] Incremental evidence append to graph during job
- [ ] Evidence delta on poll
- [ ] Lighthouse + browser cache layer
- [ ] Deprecation notice on sync `perception_seo_audit`
- [ ] Update `AGENT_GUIDE` §15 SEO playbook

### 3.3 Coordination (keep on)

- [ ] Profile bridge p95; slim briefing payload if >50ms
- [ ] Do **not** disable coordination

---

## 4. Success metrics (Phase 1)

| Metric | Target |
|--------|--------|
| `perception_health` during background SEO job | **<500ms** (not blocked) |
| `seo_audit_start` | **<500ms** p95 |
| `seo_audit_poll` | **<200ms** p95 |
| SEO job completes (warm, background) | 60–120s without blocking stdio |
| Sync timeout with partial | **0** empty `data` envelopes for SEO |
| Parallel provider speedup | ≥30% vs sequential (warm) |

---

## 5. Explicit non-goals (Phase 1)

- ❌ `resolve_route` or any resolver parser
- ❌ Removing `perception_code_context` / CRG
- ❌ Resolver framework
- ❌ Framework docs removal
- ❌ MCP Tasks native (optional later)

---

## References

- `src/navigation/execution_runtime/executor.py`
- `src/navigation/execution_runtime/policies/cancellation.py`
- `src/navigation/seo_intelligence/planning/orchestrator.py`
- `src/navigation/seo_intelligence/knowledge/graph/store.py`
- `evals/PERFORMANCE_REVIEW.md`
- [MCP Tasks overview](https://modelcontextprotocol.io/extensions/tasks/overview)
