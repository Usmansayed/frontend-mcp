# Frontend MCP — Performance Review

**Date:** 2026-07-13  
**Scope:** Installed `frontend-mcp==1.0.1` via Cursor MCP server `user-frontend-mcp`  
**Method:** Code-path analysis + end-user measurements from `evals/END_USER_MCP_EVALUATION.md` and 2026-07-13 retest  
**Constraint:** Investigation only — **no optimizations applied**

---

## Executive summary

The Frontend MCP’s core value proposition is a **deterministic browser runtime** (observe → act → verify) that the host agent cannot replicate cheaply. That layer is **mostly fast and worth keeping**.

Performance problems cluster in three areas:

1. **Code Relationship Graph (CRG)** — bundled via `code-review-graph`, invoked on every `perception_code_context` call. A factory bug forces **full graph rebuild on every call**, and missing `repo_root` can index the **entire process cwd** (often the monorepo). This blocks the MCP stdio event loop for seconds to minutes.
2. **SEO audit orchestration** — fully **sequential** pipeline (LibreCrawl + 2× Lighthouse + probes) with internal budgets of **240–330s+**, while MCP hard-limits the handler to **90s** and returns **no partial results** on timeout.
3. **Architectural event-loop blocking** — heavy sync work (CRG, Lighthouse subprocesses, file scans) runs inside `async def` handlers **without `asyncio.to_thread`**, so one slow tool can freeze **all** MCP tools.

**Strategic finding:** Several expensive subsystems duplicate what the host agent already does well (code search, reading files, reasoning). The MCP should own **browser truth**, **deterministic probes**, and **structured extraction** — not full-repo graph builds at request time.

| Classification | Count (of 71 tools) | Examples |
|----------------|---------------------|----------|
| Essential and already fast | ~35 | health, verify, flow_describe, icon_search, coordinator_briefing |
| Essential but needs optimization | ~12 | observe, session_start, build_design_snapshot, search_components |
| Heavy but valuable | ~8 | full_diagnosis, inspiration_collect, seo_audit (if redesigned) |
| Heavy with poor ROI | ~16 | code_context (as implemented), framework_docs, design_graph_refresh, seo_verify |

---

## Design principle: what belongs in the MCP?

| Host agent already has | MCP should own |
|------------------------|----------------|
| File read, grep, ripgrep, semantic search (Cursor @codebase) | Live DOM, screenshots, a11y tree, console/network from real browser |
| LLM reasoning, planning, code edits | Deterministic form probes, route-guard checks, verify criteria |
| Route/file correlation via search | Structured facts: validation rules, blocking issues, scan_ids |
| Long-running audits (user-initiated) | Fast, bounded extractions from **current page state** |

**Rule of thumb:** If a tool takes >2s cold and the host can get 80% of the value with grep + read_file in <500ms, the MCP version needs a **strong justification** (live browser coupling, deterministic replay, or facts the agent cannot infer).

---

## Deep dive: `perception_code_context`

### What it does internally

```
MCP call_tool
  → ExecutionRuntime (30s timeout)
  → handle_code_context (handlers.py:885)
  → create_code_graph (factory.py:10)
       → CRGCodeGraph.initialize()     # build_or_update_graph(full_rebuild=False, postprocess="minimal")
       → graph.query("stats")
       → if node_count == 0: rebuild()  # full_rebuild=True — BUG: checks wrong key
  → graph.query(query_type, **query_kwargs)
  → code_review_graph.tools.* (external package)
       → tree-sitter parse → SQLite (.code-review-graph/graph.db)
       → FTS5 index, optional embeddings
```

**Every call** opens SQLite, runs incremental build logic, and (due to bug) often triggers **full rebuild**.

### Why is it building a graph?

CRG (`code-review-graph>=2.3.6`) is a **standalone code intelligence product** vendored as a dependency. It builds a call/import graph for:
- semantic + keyword search
- impact radius (changed-file blast radius)
- flow/community detection (full postprocess)

FPE wraps it as `perception_code_context` for AGENT_GUIDE §10 “code ↔ UI correlation.”

### Is the graph necessary?

**For the stated MCP use case — mostly no.**

| Documented intent | What CRG actually provides | Host agent alternative |
|-------------------|---------------------------|------------------------|
| Find component for URL `/forms/validation` | Semantic search over function names | `grep "validation"` + read `router.jsx` |
| Code ↔ live UI correlation | Graph stats, search hits | observe DOM + grep component name |
| Change impact before edit | `get_impact_radius` (not exposed as `get_route`) | git diff + grep imports |

Measured results (2026-07-13, valid `repo_root`):

| Call | Repo | Latency | Result |
|------|------|---------|--------|
| `stats` | sandbox (45 files) | **703 ms** | 115 nodes, 607 edges |
| `search` "validation form" | sandbox | **562 ms** | 1 hit: `ValidationForm.jsx::validate` |
| `stats` | full monorepo (793 files) | **13,663 ms** | 4,319 nodes, 30,651 edges |
| `stats` (no `repo_root`) | cwd fallback | **>35 min hang** (interrupted) | indexing wrong tree |
| `get_route` | sandbox | **541 ms** | `ok:false` — `unknown_query_type` |

Memory (Windows, MCP python process): ~**142 MB** working set during session; graph build adds transient CPU spike (tree-sitter process pool for large repos).

### Root cause of hangs

| Issue | Type | Evidence |
|-------|------|----------|
| `node_count` vs `total_nodes` key mismatch | **Bug** | `factory.py:19` always sees 0 → `rebuild()` every call |
| Default `repo_root` → `Path.cwd()` | **Configuration** | `paths.py:30-48` when no env/sandbox |
| Sync CRG on asyncio event loop | **Architecture** | No `to_thread` in execution_runtime |
| 30s timeout vs 13s+ monorepo build | **Policy mismatch** | Large repos exceed timeout; blocks stdio before cancel |
| `get_route` not implemented | **Bug / doc drift** | Schema says `get_route`; impl has `route` (impact radius, not URL) |

### Value vs host agent

| CRG capability | Unique value | Verdict |
|----------------|--------------|---------|
| Full call graph | Marginal for frontend UI tasks | **Poor ROI in MCP** |
| Semantic search | Cursor @codebase does this with background index | **Redundant** |
| FTS keyword search | Host ripgrep is faster | **Redundant** |
| Impact radius | Useful for refactors, not browser verify loop | **Optional / separate tool** |
| Route → component | **Not implemented** despite docs | **Gap** |

### Can we remove it entirely?

**Yes, for v1 MCP mission** — with a lighter replacement:

| Approach | Cost | Coverage |
|----------|------|----------|
| **Remove** `perception_code_context`; document “use host grep” | 0 ms | 70% for UI tasks |
| **Light route resolver** — parse `react-router` / `next` config statically | <100 ms | 85% for “which file renders this URL” |
| **Lazy CRG** — background index, query-only reads | 50–200 ms warm | 95% for power users |
| **Full CRG per call** (current) | 0.7–60+ s | 100% graph features, blocks MCP |

**Recommendation: Redesign → Replace** with a **<200ms route/symbol resolver** for UI correlation; demote full CRG to optional CLI or background worker.

### Simpler 80/90% alternative

```text
perception_code_context (proposed)
  query_type: resolve_route
    → read router config (react-router-dom, next/app routes)
    → return { file, component, line } — no graph build

  query_type: find_symbol
    → delegate hint to host ("grep ValidationForm in repo")
    → OR ripgrep subprocess with 2s cap (not tree-sitter fleet)
```

---

## Deep dive: `perception_seo_audit`

### Execution pipeline (all sequential)

```
handle_seo_audit
  → SeoAuditOrchestrator.audit
       1. ensure_companions_ready (LibreCrawl: clone/pip/playwright on cold — up to 600s per step)
       2. _probe_connections (7 providers, one-by-one)
       3. for each provider: collect() sequentially
            - librecrawl: crawl poll up to 90s
            - lighthouse: performance (120s) THEN seo (120s)
            - browser: read scan_id from registry (<1s)
       4. AiVisibilityAdapter (12 analyzers, <1s, in-memory)
       5. recommendation pipeline (1–10s; +Bedrock if enabled)
```

### Why it timed out at ~90s

| Layer | Budget | Conflict |
|-------|--------|----------|
| MCP `ExecutionRuntime` | **90s** hard kill | `timeout.py:20-21` |
| Production test plan SLO | **120s** warm, **300s** cold | `PRODUCTION_TEST_PLAN.md:417-418` |
| LibreCrawl crawl wait | up to **90s** | `librecrawl/client.py` |
| Lighthouse ×2 | up to **240s** | sequential subprocess |
| Companion health wait | up to **180s** | cold start |

**Warm dev audit alone:** LibreCrawl (10–90s) + Lighthouse×2 (50–240s) = **60–330s** — always exceeds 90s MCP cap.

`include_ai_visibility` is **not** the bottleneck (milliseconds).

### Graceful degradation

| Level | Works? |
|-------|--------|
| Per-provider skip (`degraded[]`) | ✅ Inside orchestrator |
| Partial evidence returned | ✅ If handler completes |
| MCP timeout | ❌ Empty envelope, no partials |
| Wrong param `url` vs `website_url` | ❌ Validation error (config UX) |

### Value vs cost

SEO audit **is valuable** as an orchestrated report — but **cannot succeed** under current timeout architecture. The orchestrator degrades per-provider; the execution runtime does not.

**Recommendation: Redesign** — split into fast/slow tools, parallelize providers, stream partial results, align timeout with SLO (or make audit async with `audit_id` polling).

---

## Cross-cutting architectural bottlenecks

### 1. Event loop blocking (critical)

- All handlers are `async def` but CRG, Lighthouse, file walks, and some provider HTTP run **synchronously**.
- `execution_runtime/` has **zero** `asyncio.to_thread` / `run_in_executor` usage.
- **Effect:** One `code_context` or `seo_audit` blocks health, verify, and all other tools on the same MCP connection.
- **Observed:** Parallel tool batches caused 7+ minute hangs in end-user eval (not individual tool slowness alone).

### 2. No process-level singletons

- CRG: new graph build per call, no in-memory cache.
- Browser session: correctly persisted via `SessionStore`.
- Scan registry: correctly persisted.
- Coordinator PSM: in-memory per episode (fast).

### 3. Payload bloat

- `perception_navigate_and_observe` (full): **~1 MB JSON** + inline images.
- Impacts host LLM context and serialization time.
- Mitigation exists (`detail: summary_only`, `budget`) but defaults to heavy.

### 4. Timeout policy incoherence

| Tool | MCP timeout | Internal work budget |
|------|-------------|---------------------|
| `code_context` | 30s | CRG docs: 30–60s first build |
| `seo_audit` | 90s | Pipeline: 120–330s warm |
| `audit_*` / `full_diagnosis` | 120s | 4× Lighthouse possible |
| Default | 60s | — |

### 5. Initialization costs (cold start)

| Subsystem | Cold cost | When |
|-----------|-----------|------|
| Playwright browser | 2–10s | `session_start` |
| CRG full build | 0.7–60s+ | Every `code_context` call (bug) |
| LibreCrawl companion | minutes | First `seo_audit` |
| Lighthouse | 30–120s per category | Audit tools |
| Coordination artifacts | <50ms | Every tool (bundled in v1.0.1) |

---

## Industry comparison

| Product | Code context approach | Index timing | Query latency | Lesson for FPE |
|---------|----------------------|--------------|---------------|----------------|
| **Cursor** | Background semantic index + Instant Grep | Async at workspace open; sync every 5 min | Grep: ms; semantic: sub-second | **Never build index per tool call** |
| **Continue** | @codebase embeddings | Background | Sub-second | Host owns search |
| **Sourcegraph Cody** | Pre-indexed enterprise search + BM25 | Server-side continuous | ~5s TTFT (optimized) | Heavy index is **offline**, not MCP request path |
| **Aider** | Repo map (PageRank over import graph) | Per-session, **~1k token budget** | Fast, ranked subset | Graph is **small and targeted**, not full AST |
| **tree-sitter tools** | Parse on demand per file | Lazy | Per-file ms | Parse only what you need |
| **FPE CRG** | Full AST graph in SQLite | **Per call** (bug: full rebuild) | 0.7–60s+ | **Inverted** — slowest pattern |

**Consensus:** Index **in background** or **query incrementally**. MCP tools should return in **<2s** for interactive agent loops.

---

## Full tool performance audit (71 tools)

**Legend**

- **Cold:** first call in fresh MCP process / no cache
- **Warm:** repeated call with hot caches
- **Class:** 1=Essential fast, 2=Essential optimize, 3=Heavy valuable, 4=Heavy poor ROI

Measured values from end-user eval where available; estimates marked *(est.)* from code analysis.

### Core browser (15 tools)

| Tool | Cold | Warm | Memory | External deps | Blocking ops | Class | Notes |
|------|------|------|--------|---------------|--------------|-------|-------|
| `perception_health` | 200–400ms | 3ms (replay) | Low | HTTP to dev server | sync HTTP | **1** | Idempotency works |
| `perception_session_start` | 2–10s | — | +50–150MB | Playwright/Chromium | browser launch | **2** | Unavoidable; cache session |
| `perception_session_end` | <500ms | — | Frees memory | — | browser close | **1** | |
| `perception_navigate` | 200ms–2s | <500ms | Low | Browser | CDP navigate | **1** | |
| `perception_navigate_and_observe` | 3–15s | 2–8s | Med | Browser | DOM+a11y+screenshot | **2** | p95 budget 15s; ~1MB payload |
| `perception_observe` | 2–10s | 1–5s | Med | Browser | same | **2** | Use `summary_only` default? |
| `perception_execute_script` | 200ms–2s | — | Low | Browser | JS eval | **1** | |
| `perception_execute_actions` | 500ms–3s | — | Low | Browser | click/fill | **1** | |
| `perception_verify` | 100–160ms | 100ms | Low | Browser | DOM check | **1** | Excellent |
| `perception_diff` | 200ms–1s | — | Med | — | image compare | **1** | |
| `perception_auth_gate` | <500ms | — | Low | Browser | DOM heuristics | **1** | |
| `perception_probe_form` | 1–5s | — | Low | Browser | submit probes | **1** | High unique value |
| `perception_probe_guards` | 2–10s | — | Low | Browser | multi-navigate | **2** | Sequential routes |
| `perception_flow_describe` | <50ms | <15ms | Low | — | JSON read | **1** | |
| `perception_state_*` (3) | <200ms | — | Low | Browser | storage R/W | **1** | |

### Debugging & audits (10 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_console_get/clear` | <100ms | <50ms | **1** | Ring buffer |
| `perception_network_get/clear` | <200ms | <100ms | **1** | |
| `perception_audit_accessibility` | 30–120s | 30–90s | **3** | Lighthouse subprocess |
| `perception_audit_performance` | 30–120s | 30–90s | **3** | |
| `perception_audit_seo` | 30–120s | 30–90s | **3** | |
| `perception_audit_best_practices` | 30–120s | 30–90s | **3** | |
| `perception_audit_mode` | 60–480s | 60–300s | **3** | 4× sequential LH |
| `perception_full_diagnosis` | 10–180s | 5–60s | **3** | With audits: very heavy |
| `perception_debug_mode` | 2–10s | 1–5s | **2** | No Lighthouse — good tradeoff |

### Code & framework (3 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_code_context` | **0.7–60s+** | **0.5–14s** (still rebuilds) | **4** | **Remove/redesign** |
| `perception_detect_framework` | <200ms | <100ms | **1** | Reads package.json |
| `perception_framework_docs` | 2–30s | 1–10s | **4** | Spawns npx Grounded Docs |

### Component intelligence (4 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_plan_component_search` | <100ms | <50ms | **1** | No network |
| `perception_search_components` | 200ms–2s | <500ms | **2** | shadcn catalog local |
| `perception_select_component_foundation` | 500ms–3s | — | **2** | Parallel guidance; no CRG |
| `perception_integrate_component` | <50ms (dry) | 6ms | **2** | Scaffold; needs repo |

### Inspiration (3 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_inspiration_discover` | 1–5s | <2s | **2** | HTTP to design sites |
| `perception_inspiration_collect` | 10–60s | 5–30s | **3** | Headed browser, blobs |
| `perception_inspiration_session_end` | <100ms | — | **1** | |

### Resources (14 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_resource_icon_search` | <500ms | <200ms | **1** | Excellent ROI |
| `perception_resource_search` | <500ms | <200ms | **1** | |
| `perception_resource_*_search` (7) | 100ms–5s | varies | **2** | font/pattern broken |
| `perception_resource_preview` | 1–10s | — | **3** | Blobs + network |
| `perception_resource_license_check` | <50ms | — | **1** | |
| `perception_resource_observe_bridge` | 500ms–2s | — | **2** | Needs scan_id |
| `perception_resource_session_end` | <100ms | — | **1** | |

### SEO (5 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_seo_status` | ~100ms | ~99ms | **1** | |
| `perception_seo_connect` | seconds–minutes | — | **3** | OAuth interactive |
| `perception_seo_audit` | **timeout 90s** | **timeout 90s** | **3→4** | Broken under MCP cap |
| `perception_seo_query` | <200ms | <100ms | **1** | Local graph read |
| `perception_seo_verify` | **timeout 90s** | — | **4** | Re-runs full audit |

### Figma (3 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_figma_status` | <500ms | <200ms | **1** | |
| `perception_figma_connect` | 1–5s | — | **2** | PAT storage |
| `perception_figma_context` | 1–10s | 1–5s | **2** | Figma API |

### Design & consistency (9 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_build_design_snapshot` | 50–500ms | <100ms | **2** | Needs valid scan_id |
| `perception_design_review` | 9–50ms | <20ms | **1** | Snapshot-local |
| `perception_consistency_review` | 500ms–5s | — | **3** | May refresh graph |
| `perception_consistency_audit` | 200ms–2s | — | **2** | |
| `perception_design_knowledge_query` | <200ms | <100ms | **2** | |
| `perception_design_graph_summary` | <200ms | <100ms | **2** | |
| `perception_design_graph_refresh` | 1–30s | — | **4** | Full discovery pipeline |
| `perception_consistency_assess` | <100ms | — | **1** | |
| `perception_consistency_propose_fix` | <100ms | — | **1** | |

### Coordination (3 tools)

| Tool | Cold | Warm | Class | Notes |
|------|------|------|-------|-------|
| `perception_coordinator_episode_start` | <100ms | — | **1** | |
| `perception_coordinator_apply_envelope` | <50ms | — | **1** | |
| `perception_coordinator_briefing` | <100ms | — | **1** | Low overhead |

---

## Cost vs value matrix (expensive subsystems)

| Subsystem | Typical cost | Unique value | Host alternative | Verdict |
|-----------|-------------|--------------|------------------|---------|
| **CRG / code_context** | 0.7–60s+ per call | Call graph, semantic search | Cursor grep + @codebase | **Remove / replace** |
| **LibreCrawl companion** | 10–90s crawl; minutes cold | Multi-page crawl | Host fetch sitemap + curl | **Keep for seo_audit only; async** |
| **Lighthouse (in SEO audit)** | 60–240s | CWV + SEO scores | Same via dedicated audit tool | **Dedupe** — don't run 2× in seo_audit + audit_mode |
| **Lighthouse (page audits)** | 30–120s each | Page-specific scores | Worth it when scoped to one URL | **Keep** with explicit timeout |
| **Inspiration collect** | 10–60s | Headed scrape + vision blobs | Host web search | **Keep** — unique |
| **Design graph refresh** | 1–30s | Project design standards | Manual token read | **Defer / lazy** |
| **Framework docs (Grounded)** | 2–30s | Version-aware docs | Host @docs / context7 MCP | **Remove from hot path** |
| **Browser observe** | 2–15s | Live truth | None | **Keep** — core mission |
| **AI visibility analyzers** | <1s | Derived SEO signals | Host reasoning | **Keep** |
| **Coordinator PSM** | <100ms | Playbook hints | Host planning | **Keep** — good ROI |

---

## Failure mode taxonomy

| Symptom | Root cause | Bug / config / limitation |
|---------|------------|---------------------------|
| MCP hangs 7+ min | Sync CRG on event loop + parallel calls | **Architecture** + usage |
| `code_context` always slow | `node_count` bug → full rebuild | **Bug** |
| `code_context` indexes wrong repo | cwd fallback | **Configuration** |
| `get_route` fails | Query type not implemented | **Bug** |
| `seo_audit` empty at 90s | Timeout < pipeline budget | **Architecture / policy** |
| `seo_audit` validation error | Used `url` not `website_url` | **Configuration UX** |
| Font/pattern search empty | Provider not implemented / API 400 | **Limitation** |
| MCP resources 404 | Cursor resource registration | **Integration** |
| Large observe payloads | Default `detail: full` | **Design choice** |

---

## Recommendations

### Keep (no change needed)

Core browser loop, verify, probe_form, probe_guards, flow_describe, health, console/network, icon search, plan_component_search, seo_status, seo_query, design_review (from snapshot), coordinator tools, figma_status.

### Optimize (minimal changes, high impact)

| Priority | Change | Expected gain |
|----------|--------|---------------|
| P0 | Offload sync handlers to thread pool (`to_thread`) | Unblock stdio during heavy work |
| P0 | Fix `node_count` → `total_nodes` in factory | Eliminate per-call full rebuild |
| P0 | Align `seo_audit` timeout with SLO OR return partials on timeout | Audit actually completes |
| P1 | Default observe to `summary_only`; require opt-in for full DOM | −80% payload |
| P1 | Parallelize SEO provider collection | −40–60% audit time |
| P1 | Require explicit `repo_root` for code_context (fail fast) | No cwd surprise |
| P2 | Cache CRG graph handle per `repo_root` in process | Warm queries <200ms |
| P2 | Deduplicate Lighthouse runs across seo_audit and audit_* | −50% audit CPU |

### Redesign

| Feature | Proposed shape |
|---------|----------------|
| `perception_code_context` | Replace with `perception_resolve_route` (static router parse, <200ms) + optional `perception_code_impact` (lazy CRG, background) |
| `perception_seo_audit` | Split: `seo_audit_start` (async job id) + `seo_audit_poll` OR raise timeout to 180s with streaming partials |
| `perception_framework_docs` | Remove from MCP; point to context7 / host docs |
| `perception_design_graph_refresh` | Trigger only on explicit user request; never in hot path |

### Remove (candidates)

| Tool / behavior | Rationale |
|-----------------|-----------|
| Full CRG build on every `code_context` call | Host does better |
| `get_route` query_type (as documented) | Misleading; wrong semantics |
| `perception_seo_verify` full re-audit | Compare against cached audit_id instead |
| SEO audit inside 90s synchronous MCP call | Cannot meet SLO |

---

## Prioritized optimization roadmap

### Phase 0 — Stop the bleeding (1–2 days, minimal fixes)

1. Fix `total_nodes` check in `factory.py` — stop full rebuild every call
2. `asyncio.to_thread` for CRG and Lighthouse in handlers
3. Fail fast when `repo_root` missing for `code_context` (require explicit path)
4. Rename/fix `get_route` → implement real route resolver OR remove from schema
5. Raise `seo_audit` timeout to 180s **or** return partial envelope on timeout

### Phase 1 — Architecture alignment (1 week)

1. Replace `code_context` with lightweight `resolve_route` for AGENT_GUIDE §10
2. Parallel SEO provider collection
3. Default observe `summary_only: true`
4. Process-level CRG cache (optional background warm on `repo_root` set)
5. Document “one tool at a time” until thread pool proven

### Phase 2 — Strategic simplification (2–4 weeks)

1. Async SEO audit job model
2. Consolidate Lighthouse entry points
3. Remove `framework_docs` from MCP surface
4. Lazy design graph refresh
5. Performance CI gate on p95 for top 10 tools

### Phase 3 — Measure and enforce

1. Run `src/run_performance_baseline.py` in CI against sandbox
2. Add per-tool metrics export from execution_runtime ledger
3. Publish cold/warm tables in each release

---

## Minimal fixes required (investigation conclusion)

**Do not optimize CRG yet — question existence first.** If keeping any code context:

| # | Fix | Type | Effort |
|---|-----|------|--------|
| 1 | `node_count` → `total_nodes` | Bug | Trivial |
| 2 | Thread-pool offload for blocking handlers | Architecture | Small |
| 3 | Require `repo_root` (no cwd fallback) | Config | Trivial |
| 4 | Implement `resolve_route` OR remove `get_route` from schema | Design | Small |
| 5 | SEO: timeout ≥180s OR partial results on timeout | Policy | Small |
| 6 | SEO: parallel provider collect | Perf | Medium |

**Highest ROI strategic change:** Replace per-call CRG with **static route resolution** for the browser↔code loop; let the host agent own search.

---

## Appendix: measured session data (2026-07-13)

```
perception_code_context stats  sandbox     703 ms   ok
perception_code_context search sandbox     562 ms   ok
perception_code_context stats  monorepo  13663 ms   ok
perception_code_context stats  no root   >35 min    interrupted
perception_code_context get_route        541 ms   ok:false unknown_query_type

perception_health                          3 ms   ok (warm)
perception_integrate_component             6 ms   ok degraded
perception_seo_audit                   90015 ms   timeout (prior session)

MCP python process: ~142 MB working set, ~119 MB private (Windows)
```

---

## References

- `src/navigation/codebase_intelligence/graph/factory.py` — CRG init + rebuild trigger
- `src/navigation/codebase_intelligence/graph/crg_impl.py` — query type dispatch
- `src/navigation/core/paths.py` — default `repo_root`
- `src/navigation/execution_runtime/policies/timeout.py` — per-tool timeouts
- `src/navigation/seo_intelligence/planning/orchestrator.py` — sequential SEO pipeline
- `evals/END_USER_MCP_EVALUATION.md` — hands-on latency evidence
- `docs/PRODUCTION_TEST_PLAN.md` — performance budgets (conflict with 90s SEO cap)
- Cursor: [Semantic search blog](https://cursor.com/blog/semsearch), [Agent search docs](https://cursor.com/docs/agent/tools/search)
- Aider: [Repository map](https://aider.chat/docs/repomap.html)
