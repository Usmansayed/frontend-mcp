# Frontend MCP — Architecture Rethink

**Date:** 2026-07-13  
**Status:** Research & recommendations — **refined per stakeholder review; no implementation yet**  
**Prerequisite:** [`evals/PERFORMANCE_REVIEW.md`](PERFORMANCE_REVIEW.md)

---

## Guiding principle

> **The MCP provides deterministic capabilities and live runtime intelligence.  
> The host agent provides reasoning, code understanding, and planning.**

The MCP must feel **instant** in normal agent loops (observe → reason → act → verify). Anything that takes seconds to minutes belongs in **background jobs**, **cached evidence**, or **the host agent** — not in synchronous stdio tool calls.

This document challenges every expensive subsystem and proposes a **host–MCP collaboration model** instead of duplicating IDE-grade code intelligence inside the MCP.

### Performance philosophy (formal rules)

These three rules govern every tool and subsystem decision:

1. **If the host already does it well, don't duplicate it.**  
   (grep, semantic search, framework docs, open-ended code exploration)

2. **If the MCP can answer deterministically in under ~200 ms, keep it.**  
   (static route parse, token extraction, validate claims, browser verify)

3. **If it takes seconds or minutes, move it to async/background unless explicitly requested.**  
   (full SEO audit, inspiration collect, multi-category Lighthouse, PDG full refresh)

### Stakeholder-approved direction (2026-07-13)

| Decision | Status |
|----------|--------|
| Remove `perception_code_context` from hot path | **Adopt** |
| Lightweight `resolve_*` + `validate_*` tools | **Adopt** |
| SEO as async jobs (start + poll) | **Adopt** |
| Remove framework docs from MCP | **Adopt** |
| Browser Intelligence as primary differentiator | **Adopt** |
| Coordination default **off** (`COORDINATION_DISABLED=1`) | **Rejected** — see §3.8 |
| Host provides **all** structured claims | **Rejected** — hybrid model; see §2 |

**Coordination refinement:** Keep coordination **on by default**. It should be **invisible** (~few ms), not optional. If it materially slows execution, **optimize** the bridge — don't disable the investment.

**Resolve vs validate refinement:** Use **MCP-native tiny parsers** for common deterministic tasks (React Router config, Tailwind tokens) because they are fast and predictable. Use **agent claims + validate** for ambiguous or project-specific cases — not as the only path.

---

## 1. The core architectural shift

### What we assumed (old)

| Assumption | Consequence |
|------------|-------------|
| MCP should understand the codebase | CRG full graph build per call |
| MCP should fetch framework docs | npx Grounded Docs subprocess |
| MCP should run full SEO audit synchronously | 90s timeout, empty results |
| MCP should maintain Project Design Graph eagerly | Multi-source refresh on review |
| More tools = more value | 71 tools, context bloat, blocking |

### What we should assume (new)

| Assumption | Consequence |
|------------|-------------|
| Host already has grep, @codebase, file read | MCP **validates** agent claims, does not re-index |
| Browser truth is unique to MCP | Observe, probe, verify stay first-class |
| Long audits are jobs, not tool calls | Call-now, fetch-later (MCP Tasks pattern) |
| Structured facts beat reasoning in MCP | Small deterministic `resolve_*` tools |
| Agent plans; MCP executes & verifies | Coordinator stays **on** — lightweight, invisible advisory layer |

### The collaboration pattern: **Resolve first, validate when needed**

Hybrid model — not “host provides everything”:

```text
┌─────────────────────────────────────────────────────────────────┐
│ COMMON DETERMINISTIC PATH (preferred, <200ms)                    │
│  MCP: resolve_route / resolve_design_token / resolve_component │
│  • tiny static parsers on known config files only                │
│  • no graph, no repo walk                                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ AMBIGUOUS / COMPLEX PATH (host + MCP)                            │
│  Host: grep / @codebase → structured claim JSON                  │
│  MCP: validate_*_claim → correlate_live(scan_id)                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ALWAYS MCP (unique runtime truth)                                │
│  observe · probe · verify · console · network · screenshots      │
└─────────────────────────────────────────────────────────────────┘
```

**When to use which path:**

| Situation | Path |
|-----------|------|
| Standard react-router / Next app route lookup | `resolve_route` (MCP parser) |
| Tailwind / CSS token extraction | `resolve_design_token` (MCP parser) |
| Dynamic routes, lazy imports, monorepo ambiguity | Host search → `validate_*_claim` |
| Confirm code matches live UI | `correlate_live` after observe |

---

## 2. Lightweight `resolve_*` capabilities

Replace `perception_code_context` (CRG) with **MCP-native resolvers** (common cases) plus **validation** (ambiguous cases). No full graph.

### 2.1 Proposed tools

| Tool | What MCP does (deterministic) | When host involved | Target latency |
|------|------------------------------|-------------------|----------------|
| `perception_resolve_route` | Parse static router config (react-router, next/app, remix) | Fallback for edge cases | **<200ms** |
| `perception_validate_route_claim` | Verify agent claim: file exists, export matches, path in router | Dynamic/lazy routes | **<100ms** |
| `perception_resolve_component` | Map component name → file via `components.json` + folder conventions | Unusual layouts | **<100ms** |
| `perception_validate_component_claim` | Check file exports, props surface, duplicate in `components/` | Agent-found candidates | **<100ms** |
| `perception_resolve_api_endpoint` | Regex scan known API entry files (`fetch`, tRPC, Hono) | Custom routing | **<300ms** |
| `perception_resolve_design_token` | Read `tailwind.config`, CSS variables, DTCG JSON | — | **<100ms** |
| `perception_resolve_layout` | Extract from `DesignSnapshot` (already exists) | — | **<50ms** |
| `perception_resolve_state_owner` | Parse zustand/redux/context store files (shallow) | Obscure state libs | **<200ms** |
| `perception_correlate_live` | Given `scan_id` + resolve/claim result, check DOM markers | — | **<500ms** |

**Default workflow:** try `resolve_*` first. Escalate to host search + `validate_*` only when resolve returns `confidence: low` or `ambiguous: true`.

**No call graph. No tree-sitter fleet. No SQLite rebuild.**

### 2.2 Static route resolution (example)

Sandbox `router.jsx` is declarative — parseable without a graph:

```43:91:sandbox/src/router.jsx
export const createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: <Layout />,
    children: [
      // ...
      {
        path: 'forms',
        element: <FormsLayout />,
        children: [
          { path: 'validation', element: <ValidationForm /> },
```

**Implementation sketch (future):**
- Detect framework via existing `perception_detect_framework` (<200ms)
- Run framework-specific **static parser** (regex/AST-lite on router file only)
- Return `{ route, file, component, line, confidence: "static" }`

**Coverage:** ~85–90% for standard React Router / Next.js App Router projects. Edge cases (dynamic routes, lazy `import()`) → agent claim + validate.

### 2.3 Agent claim schema (strict)

Host agent returns claims; MCP validates. Example for route correlation (AGENT_GUIDE §10):

```json
{
  "claim_type": "route_component",
  "route": "/forms/validation",
  "repo_root": "/path/to/app",
  "component": {
    "name": "ValidationForm",
    "file": "src/pages/forms/ValidationForm.jsx",
    "export": "default",
    "evidence": [
      { "file": "src/router.jsx", "line": 89, "snippet": "element: <ValidationForm />" }
    ]
  },
  "confidence": "agent_inferred"
}
```

MCP `perception_validate_route_claim`:
1. `file` exists under `repo_root`
2. `component.name` appears in `file`
3. Static `resolve_route` agrees OR evidence lines match file content
4. Returns `{ valid: true|false, checks: [...], mcp_resolve: {...} }`

**MCP never searches the whole repo** — it checks what the agent asserted.

### 2.4 What to remove

| Remove / deprecate | Replace with |
|--------------------|--------------|
| `perception_code_context` + CRG | `resolve_route` + `validate_*_claim` + host grep |
| `get_route` query type | `resolve_route` or `validate_route_claim` |
| `code-review-graph` per-call build | Optional **background** indexer (separate process, not MCP stdio) |
| CRG in SEO `codebase_bridge` | Agent file hints + `validate_claim` |

### 2.5 When a graph might still exist (optional, not default)

If power users need impact radius:
- **Separate CLI** (`code-review-graph` already is one)
- **Background daemon** started by user, not MCP
- **Read-only query** against warm SQLite — never build in request path

This mirrors **Sourcegraph** (offline index) and **Cursor** (background index at workspace open) — never **Aider’s mistake at MCP scale** (repo map is small/token-budgeted, not full AST per call).

---

## 3. Subsystem-by-subsystem rethink

### 3.1 Code Context (CRG) — **Remove from MCP hot path**

| Dimension | Current | Proposed |
|-----------|---------|----------|
| Cost | 0.7s–60s+ per call; blocks event loop | <200ms resolvers; validation <100ms |
| Unique value | Call graph, semantic search | **Low** — host @codebase does this |
| Host overlap | **Very high** | Invert: agent searches, MCP validates |
| Verdict | **Remove** | Replace with `resolve_*` + `validate_*` |

**Industry:** Cursor uses background embeddings + Instant Grep ([docs](https://cursor.com/docs/agent/tools/search)). Continue uses @codebase. Aider uses a **~1k-token PageRank repo map**, not full AST per request ([Aider repo map](https://aider.chat/docs/repomap.html)).

---

### 3.2 SEO Audit — **Redesign as async evidence platform**

#### Problem today

- Sequential pipeline: companion boot → 7 probes → LibreCrawl (90s) → Lighthouse×2 (240s)
- MCP timeout **90s** vs SLO **120–300s**
- Timeout returns **empty envelope** — orchestrator degradation is wasted
- `seo_verify` re-runs **entire audit**

#### Proposed architecture: **Evidence store + job model**

```text
FAST (sync, <2s)                    SLOW (async jobs)
─────────────────                   ─────────────────
perception_seo_status               perception_seo_audit_start
perception_seo_snapshot             → returns audit_job_id immediately
  (from scan_id + URL)              perception_seo_audit_poll
perception_seo_evidence_list          → status, progress%, partial evidence[]
perception_seo_query                perception_seo_audit_cancel
  (existing graph reads)          Background worker:
perception_seo_quick_check            • parallel provider collect
  (Lighthouse SEO only, 1 page)       • append evidence to graph
                                      • notify via poll interval
perception_seo_verify               perception_seo_verify
  (compare job evidence to          → diff against audit_id
   baseline, NO re-crawl)
```

#### MCP Tasks alignment

MCP spec (2025–2026) defines **Tasks**: call-now, fetch-later ([MCP Tasks overview](https://modelcontextprotocol.io/extensions/tasks/overview)):
1. `audit_start` returns `taskId` + `pollIntervalMs`
2. Client polls `tasks/get` or `perception_seo_audit_poll`
3. Terminal states: `completed`, `failed`, `cancelled`
4. `input_required` for OAuth (GSC) — pause job, resume after connect

**Until MCP Tasks are widely supported in Cursor:** implement job polling as **first-class tool** (`audit_start` / `audit_poll`) — same semantics, tool-native.

#### Incremental collection

| Provider | Incremental strategy | Cache key |
|----------|---------------------|-----------|
| **Browser** | Read `scan_id` from registry | `scan_id` + URL |
| **Lighthouse** | Skip if LHR exists for URL < TTL (e.g. 1h) | `url` + category + session |
| **LibreCrawl** | Crawl job separate; poll status; merge pages as they arrive | `website_url` + crawl_id |
| **GSC / GA4** | API responses cached 15–60 min | property + date range |
| **AI Visibility** | Derive when ≥1 evidence domain present | evidence_ids |

Run **independent providers in parallel** (`asyncio.gather`), not sequential.

#### Partial results envelope

```json
{
  "ok": true,
  "data": {
    "audit_job_id": "audit_abc123",
    "status": "running",
    "progress": { "completed_providers": ["browser"], "pending": ["lighthouse", "librecrawl"] },
    "evidence_count": 12,
    "degraded": ["lighthouse_pending"],
    "partial_summary": { "critical_issues": 2, "pages_crawled": 0 }
  }
}
```

Never return empty on timeout — persist job, return `audit_job_id` for poll.

#### Fast follow-up queries (already built!)

`perception_seo_query` reads `SeoKnowledgeGraphStore` (~100ms) — **keep and promote** as primary post-audit interface. Agents should:
1. `seo_audit_start` → poll until sufficient evidence
2. `seo_query` for `page.issues`, `audit.diff`, `graph.summary`
3. `seo_verify` diffs recommendations vs **cached audit_id**, not re-crawl

#### Quick-check mode

For interactive loops: `perception_seo_quick_check({ url, scan_id })` — browser evidence + single Lighthouse SEO category, **<60s**, sync. Full audit remains async.

**Industry:** Lighthouse CI uses collect → assert → upload as separate stages with filesystem cache ([LHCI architecture](https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/architecture.md)). Production audit platforms model jobs as `queued | running | complete` ([audit platform pattern](https://sameersabir.dev/blog/building-website-audit-platform-nextjs-playwright-lighthouse)).

---

### 3.3 Framework Docs — **Remove from MCP**

| Dimension | Current | Proposed |
|-----------|---------|----------|
| Cost | 2–30s (npx Grounded Docs) | 0ms in MCP |
| Unique value | Version-tied docs | **Low** — context7 MCP, @docs, web |
| Host overlap | **Very high** | Agent uses context7 / Cursor docs |

**Keep:** `perception_detect_framework` (<200ms) — returns stack facts for agent prompts.  
**Remove:** `perception_framework_docs` from MCP surface.  
**Component integration:** Stop calling Grounded Docs in `read_documentation`; link to install command + registry metadata only.

---

### 3.4 Design Graph (PDG) — **Lazy, snapshot-first**

| Dimension | Current | Proposed |
|-----------|---------|----------|
| Cost | 1–30s refresh; consistency_review auto-refreshes | <200ms reads; refresh on demand |
| Unique value | Token math vs live snapshot | **Medium** — deterministic consistency checks |
| Host overlap | Medium (reading tailwind.config) | MCP owns **live snapshot** correlation |

**Proposed split:**

| Tool | When | Cost |
|------|------|------|
| `build_design_snapshot` | After observe | 50–500ms |
| `design_review` | Snapshot-local critique | <50ms |
| `resolve_design_token` | Read config files | <100ms |
| `consistency_assess` | Point check vs cached graph | <100ms |
| `design_graph_refresh` | **Explicit only** | 1–30s background OK |
| `consistency_review` | **Do not auto-refresh** | Split into assess + optional refresh |

Default `enabled_sources: ['snapshot', 'tokens']` — skip Figma/Context7/codebase walk unless requested.

---

### 3.5 Component Intelligence — **Search fast, integrate thin**

| Tool | Verdict | Notes |
|------|---------|-------|
| `plan_component_search` | **Keep** | <100ms, no network |
| `search_components` | **Keep** | Local shadcn catalog |
| `select_component_foundation` | **Simplify** | Drop heavy guidance; host picks |
| `integrate_component` | **Thin scaffold** | Dry-run plan only; host installs |

Codebase guidance already uses **package.json heuristics** (not CRG) — keep that pattern.

---

### 3.6 Inspiration — **Discover sync, collect async**

| Tool | Verdict |
|------|---------|
| `inspiration_discover` | **Keep** — 1–5s, URLs only |
| `inspiration_collect` | **Async job** — headed browser + blobs |
| `inspiration_session_end` | **Keep** |

Unique value (gallery adapters, vision blobs) — host cannot easily replicate. But collect must not block stdio.

---

### 3.7 Lighthouse / Frontend Quality — **Dedupe and scope**

| Tool | Verdict |
|------|---------|
| `audit_{category}` (single) | **Keep** — explicit, 30–120s |
| `debug_mode` | **Keep** — fast path, no LH |
| `audit_mode` (4×) | **Async job** or remove |
| `full_diagnosis` | **Default `run_audits: false`** |

**Rule:** One Lighthouse run per URL per session — share LHR between SEO audit and `audit_*` via artifacts cache.

---

### 3.8 Coordination Intelligence — **Keep on; make invisible**

| Dimension | Current | Proposed |
|-----------|---------|----------|
| Cost | <100ms per tool (bridge on every call) | **Stay on by default**; target <50ms |
| Unique value | Playbook hints, PSM, compiled verify steps | **Worth keeping** if lightweight |
| Host overlap | High for planning | Coordinator advises; host decides |

**Stakeholder decision:** Do **not** default `COORDINATION_DISABLED=1`. The coordinator investment should pay off as an **invisible advisory layer**, not an opt-in feature.

**Optimization targets (if bridge exceeds ~50ms p95):**
- Lazy-load runtime artifacts only once (already `@lru_cache`)
- Slim envelope `data.coordinator` payload — briefing summary only, not full PSM dump
- Skip re-compilation when envelope `ok` unchanged and capability unchanged
- Profile `process_tool_envelope` in hot path; offload only if sync work found

**Keep:** `flow_describe` as static flow graphs; coordinator enriches cross-tool episode state.

**Remove from report (rejected):** ~~`COORDINATION_DISABLED=1` as default for installed MCP~~

---

## 4. Target tool taxonomy (post-rethink)

### Tier A — Interactive loop (<2s, sync)

Core browser, verify, probe, health, flow_describe, resolve_*, validate_*_claim, seo_status, seo_snapshot, seo_query, design_review (from snapshot), icon_search, plan_component_search, **coordinator_briefing** (always on).

### Tier B — Session-scoped (2–15s, sync, explicit)

session_start, navigate_and_observe (default `summary_only`), build_design_snapshot, search_components, inspiration_discover, single Lighthouse category, figma_context.

### Tier C — Background jobs (async, poll)

seo_audit, seo_verify (diff only), inspiration_collect, design_graph_refresh, audit_mode, full_diagnosis with audits.

### Tier D — Remove or agent-only

code_context (CRG), framework_docs, full graph refresh in hot paths, seo_verify full re-audit.

---

## 5. Industry comparison

| Product | Code understanding | Long-running work | MCP/agent split |
|---------|-------------------|-------------------|-----------------|
| **Cursor** | Background index + grep; agent chooses tool | Subagents, Explore mode | Agent searches; tools execute |
| **Continue** | @codebase embeddings | — | Host-indexed |
| **Claude Code** | File read, grep, bash; Skills lazy-load | Sandboxed bash | [Hybrid MCP architecture](https://claudelab.net/en/articles/api-sdk/claude-mcp-hybrid-architecture-design-patterns): deterministic tools + LLM orchestration |
| **Aider** | Small PageRank repo map (~1k tokens) | — | Map in context, not per-tool build |
| **Sourcegraph Cody** | Pre-indexed enterprise search | Server-side | Offline index, fast query |
| **context7 MCP** | On-demand docs fetch | — | Docs outside main MCP |
| **FPE (today)** | CRG per call | Sync seo_audit | **Inverted** — duplicates host, blocks on heavy work |
| **FPE (proposed)** | Agent search + MCP validate | Async audit jobs | **Aligned** with industry |

**Anthropic / MCP community direction:**
- [Code execution MCP](https://github.com/marc-shade/code-execution-mcp) — progressive tool discovery, process data in sandbox, return summaries
- [MCP Tasks](https://modelcontextprotocol.io/extensions/tasks/overview) — call-now, fetch-later for CI/ETL-style work
- [MCP vs CLI (2026)](https://manveerc.substack.com/p/mcp-vs-cli-ai-agents) — Skills abstract transport; lazy-load by default

---

## 6. Challenge matrix: should this exist in the MCP?

| Capability | Host does well? | MCP unique? | Verdict |
|------------|----------------|-------------|---------|
| grep / semantic search | ✅ | ❌ | **Agent** |
| Read router file | ✅ | ❌ | **Agent proposes** |
| Validate file exists / route matches | Partial | ✅ | **MCP validate** |
| Live DOM / screenshot | ❌ | ✅ | **MCP** |
| Form validation probe | ❌ | ✅ | **MCP** |
| Verify criteria | ❌ | ✅ | **MCP** |
| Framework docs | ✅ (context7) | ❌ | **Agent** |
| Detect framework from package.json | ✅ | ✅ fast | **MCP** (tiny) |
| Full call graph | ✅ (@codebase) | ❌ | **Remove** |
| Lighthouse scores | Partial | ✅ tied to session | **MCP** (cached, scoped) |
| Multi-provider SEO crawl | ❌ | ✅ | **MCP async** |
| Design token file read | ✅ | ✅ | **Either** — MCP if tied to snapshot |
| Inspiration gallery scrape | Partial | ✅ | **MCP async** |
| Playbook planning | ✅ | ❌ | **Agent** |
| shadcn catalog search | Partial | ✅ structured | **MCP** |

---

## 7. Proposed MCP contract changes (future)

### 7.1 New tools (lightweight)

```
perception_resolve_route
perception_validate_route_claim
perception_validate_component_claim
perception_resolve_design_token
perception_resolve_layout          # from snapshot_id
perception_correlate_live          # scan_id + claim → DOM check
perception_seo_audit_start
perception_seo_audit_poll
perception_seo_snapshot            # fast evidence from scan_id
perception_seo_quick_check         # single-page sync SEO
```

### 7.2 Deprecated tools

```
perception_code_context            → resolve_* + validate_* + host search
perception_framework_docs          → context7 / host
perception_seo_audit (sync)        → audit_start + poll
perception_seo_verify (full)       → verify against audit_id
```

### 7.3 AGENT_GUIDE §10 rewrite (conceptual)

```text
NEW (hybrid — resolve first):
  1. MCP: perception_resolve_route({ route, repo_root })
     → if confidence high: use result
     → if ambiguous: host grep + perception_validate_route_claim({ claim })
  2. MCP: perception_navigate_and_observe({ url })
  3. MCP: perception_correlate_live({ scan_id, resolution })
  4. MCP: perception_verify(...)

OLD (deprecated):
  perception_code_context({ query_type: "search", ... })
```

---

## 8. SEO fast architecture (detailed)

### 8.1 Job state machine

```text
submitted → bootstrapping_companions → collecting → analyzing → completed
                │                              │
                └→ degraded (partial)          └→ input_required (OAuth)
failed / cancelled
```

### 8.2 Progress streaming

Poll response includes:

- `status`, `progress_pct`, `current_provider`
- `evidence_added_since_last_poll: [...]` (delta, not full graph)
- `degraded: [...]`
- `estimated_remaining_s` (heuristic from provider history)

Optional: MCP Tasks `notifications/tasks` when Cursor supports push.

### 8.3 Evidence cache layers

| Layer | Storage | TTL |
|-------|---------|-----|
| L1 | In-memory per job | Job lifetime |
| L2 | `SeoKnowledgeGraphStore` (`.cache/seo_graph.json`) | Persistent |
| L3 | Lighthouse JSON in artifacts dir | Per session |
| L4 | LibreCrawl crawl snapshot | Per website |

### 8.4 Provider parallelism

```python
# Conceptual — not implemented
results = await asyncio.gather(
    collect_browser(scan_id),
    collect_lighthouse(url, cache_ttl=3600),
    collect_librecrawl(url, max_wait=90),
    return_exceptions=True,
)
```

### 8.5 Normal workflow timing (target)

| Step | Target |
|------|--------|
| `seo_audit_start` | <500ms (returns job id) |
| First poll with browser evidence | <3s |
| Full audit complete (warm) | 60–120s **in background** |
| `seo_query` follow-up | <200ms |
| Agent continues other work | **Non-blocking** |

---

## 9. Implementation phases (stakeholder-prioritized)

> **Do not start `resolve_route` until Phase 1 is solid.**  
> The biggest architectural risk is the **async execution model**, not parsers.

| Phase | Focus | Design doc |
|-------|-------|------------|
| **1** | Execution runtime + SEO async jobs | [`ASYNC_EXECUTION_MODEL.md`](ASYNC_EXECUTION_MODEL.md) |
| **2** | Resolver framework + React Router reference | [`RESOLVER_ARCHITECTURE.md`](RESOLVER_ARCHITECTURE.md) |
| **3** | Remaining resolvers + deprecate `code_context` | Same contract |
| **4** | Consolidate heavy tools + measure | — |

### Phase 0 — Policy & docs (no code)

1. Adopt guiding principle in `AGENT_GUIDE.md` and MCP tool descriptions
2. Mark `code_context`, `framework_docs`, sync `seo_audit` as **deprecated** in docs
3. Document agent claim schemas for validate tools (used in Phase 2+)

### Phase 1 — Execution runtime + SEO async (**highest value**)

**Goal:** MCP stdio never blocked; SEO returns job id immediately.

1. **Execution runtime**
   - Tier registry: SYNC_FAST / SYNC_OFFLOAD / BACKGROUND
   - `asyncio.to_thread` (thread pool) for all sync-heavy handlers
   - Wire `CancellationToken` into offload + jobs
   - Progress reporting on long work
   - Timeout partial handoff (job_id in `data`, not empty envelope)

2. **SEO async jobs**
   - `perception_seo_audit_start` / `perception_seo_audit_poll` / `perception_seo_audit_cancel`
   - Parallel provider collection (`asyncio.gather`)
   - Partial results + evidence delta on poll
   - Evidence cache (Lighthouse, browser scan, graph store)
   - Deprecate sync `perception_seo_audit` path

3. **Coordination:** profile bridge; optimize if >50ms — **keep enabled**

See [`ASYNC_EXECUTION_MODEL.md`](ASYNC_EXECUTION_MODEL.md) for full checklist.

### Phase 2 — Resolver framework (**design before parsers**)

**Goal:** Freeze contract; replace `code_context` with pluggable resolvers.

1. **Do not jump to parser code first.** Implement:
   - `ResolverContract`, `ResolverResult`, `ResolverStatus`, `ConfidenceLevel`
   - Plugin registry + `can_handle` / priority
   - Ambiguity + fallback hints
   - Validator contract + composition with `validate_*`
   - SYNC_OFFLOAD integration (Phase 1)

2. **Reference implementation:** React Router v6 static plugin only

3. **Then extend plugins:** Next.js App Router → Remix → TanStack Router

4. Deprecate `perception_code_context`; remove CRG from MCP handler path

See [`RESOLVER_ARCHITECTURE.md`](RESOLVER_ARCHITECTURE.md).

### Phase 3 — Remaining lightweight resolvers (shared contract)

All implement same `ResolverContract`:

- `resolve_component`
- `resolve_design_token`
- `resolve_layout`
- `resolve_state_owner`
- `resolve_api_endpoint`
- `correlate_live`
- `validate_route_claim`
- `validate_component_claim`

### Phase 4 — Consolidate + measure

1. Lighthouse dedupe cache across SEO + audit tools
2. Remove `framework_docs` from MCP
3. PDG refresh explicit-only
4. Inspiration collect → async job (reuse Phase 1 job runner)
5. MCP Tasks native support when host ready
6. p95 budgets: Tier A <2s, Tier B <15s, Tier C non-blocking
7. CI performance gate (`run_performance_baseline.py` expanded)

---

## 10. Success criteria

The rethink succeeds when:

1. **Observe → verify loop** never blocks on code indexing
2. **Agent §10 workflow** uses validate + correlate, not graph search
3. **SEO audit** returns job id in <500ms; agent polls while working
4. **seo_query** is the primary SEO reasoning interface (<200ms)
5. **Installed MCP** feels instant for 90% of tool calls
6. **Tool count** decreases or tiers are clearly documented (A/B/C)
7. **No capability** duplicates Cursor grep / @codebase without unique browser coupling

---

## 11. Summary recommendations

| Area | Action |
|------|--------|
| **Code understanding** | **Phase 2–3:** Resolver framework + plugins; remove CRG. **Not Phase 1.** |
| **SEO** | **Async job model** with poll, partial evidence, parallel providers, cached graph. Keep sources of truth. |
| **Framework docs** | **Remove** from MCP; keep `detect_framework`. |
| **Design graph** | **Lazy refresh**; snapshot-first; `resolve_design_token` for fast path. |
| **Components** | **Keep search/plan**; thin integrate. |
| **Inspiration** | **Discover sync, collect async.** |
| **Lighthouse** | **Dedupe**; single-category default; async for full mode. |
| **Coordination** | **Keep on** — optimize bridge to <50ms; invisible advisory |
| **Architecture** | **Thread pool** for any sync work; never block stdio. |
| **MCP protocol** | Adopt **Tasks** pattern for Tier C tools. |

---

## References

### Internal
- `evals/PERFORMANCE_REVIEW.md`
- `evals/ASYNC_EXECUTION_MODEL.md` — **Phase 1 design**
- `evals/RESOLVER_ARCHITECTURE.md` — **Phase 2 design (freeze before parsers)**
- `src/navigation/codebase_intelligence/graph/factory.py`
- `src/navigation/seo_intelligence/planning/orchestrator.py`
- `src/navigation/seo_intelligence/knowledge/graph/store.py`
- `src/navigation/mcp/tools.py`
- `docs/PRODUCTION_TEST_PLAN.md`

### External
- [Cursor: Semantic search](https://cursor.com/blog/semsearch)
- [Cursor: Agent search tools](https://cursor.com/docs/agent/tools/search)
- [Aider: Repository map](https://aider.chat/docs/repomap.html)
- [MCP Tasks specification](https://modelcontextprotocol.io/extensions/tasks/overview)
- [Claude MCP hybrid architecture](https://claudelab.net/en/articles/api-sdk/claude-mcp-hybrid-architecture-design-patterns)
- [MCP vs CLI for agents (2026)](https://manveerc.substack.com/p/mcp-vs-cli-ai-agents)
- [Lighthouse CI architecture](https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/architecture.md)
- [Anthropic: Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
