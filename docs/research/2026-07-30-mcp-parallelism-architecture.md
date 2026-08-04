# Research: MCP Parallelism Architecture — Pros, Cons, Plan Inputs

**Date:** 2026-07-30  
**Version under study:** `1.2.0.dev57` (Evidence Pack Loop)  
**Status:** Research / planning input — **not** an implementation plan yet  
**Related:** Evidence Pack Loop, Resource Intelligence, Inspiration concurrency, `docs/PERFORMANCE_TOOL_CLASSIFICATION.md`

---

## 1. Goal of this note

We want the Frontend Perception MCP to feel **extremely fast** for work that does not depend on live browser state (inspiration scout, resource kit, component shortlist, resolvers, license rank), while remaining **reliable** for browser truth (observe / LOOK / verify).

This document captures **current architecture**, **pros/cons**, and **constraints** so we can plan implementation without painting ourselves into a corner.

**Working thesis (from product discussion):**

- Parallelize **independent intelligences inside the server** (and optionally prefetch).
- Keep **browser serial per `session_id`**.
- Prefer **one gateway call per family** over more MCP tools (tool diversity → neglect).
- Do **not** merge Resource + Component codebases; do **not** (yet) add `resources` as a separate pack-critical family.

---

## 2. Architecture map (current)

```text
Host agent (Cursor)
    │  tools/call (typically one at a time for browser)
    ▼
MCP server (navigation.mcp)
    │  ToolExecutor.execute_tool  ← one invocation path; no multi-tool scheduler
    ▼
Coordination bridge  →  episode / PSM / agent_summary.card / evidence pack
    │
    ├── Browser path (SERIAL ownership)
    │     SessionStore (logical session_id)
    │         └── BrowserSessionManager (one primary Chromium per process)
    │               navigate / observe / verify / VF / probes / guest park-restore
    │
    └── Non-browser intelligences (INTERNAL parallel already in places)
          ├── Inspiration  (multi_scout, HTTP gather, discover_token cache)
          ├── Resources    (provider asyncio.gather)
          ├── Components   (multi-pass provider gather; shadcn catalog warm)
          ├── Resolvers    (SYNC_OFFLOAD thread pool)
          └── Design / consistency / UX KB (mostly sync per call)
```

### 2.1 Tool surface

| Fact | Detail |
|------|--------|
| Approx. tool count | **~75** `perception_*` tools |
| Groups | Session, Browser, Quality, Resolver, Component, Design, **Resources (~13)**, Inspiration (~5), Diagnostics, Coordinator |
| Catalog | `src/navigation/mcp/tools.py`, `tool_catalog.py` |
| Agent rule | “One browser tool at a time per `session_id`” — **policy in instructions**, not a hard server mutex on page ops |

Resources expose a **gateway** (`perception_resource_search`) plus category shortcuts that funnel to the same handler — good pattern, but still a large discoverable set.

### 2.2 Evidence Pack / face card (what agents actually follow)

Primary contract: `agent_summary.card` (`evidence_band`, `pack`, `implement_blocked`, `next`, `owed`, …).

| Class (heavy / very_heavy) | Pack families (approx) |
|----------------------------|-------------------------|
| greenfield | inspiration → visual_feedback → component → observe → verify |
| redesign | observe → snapshot → visual_feedback → component? → verify |
| feature | observe → component? → visual_feedback → verify |
| hotfix / forms | observe/forms → verify |

**Important naming trap:** `card.resource` is usually `perception://spine/{class}` (methodology URI). It is **not** Resource Intelligence. Portfolio can map `resource_workflow` → family `resources`, but **Evidence Pack phases do not include `resources` today** — assets stay optional/advisory.

### 2.3 Browser ownership

| Fact | Detail |
|------|--------|
| Process model | **One primary Chromium** per MCP process; many logical `session_id`s share it |
| Lock | `BrowserSessionManager` locks **lease acquire/release**, not full tool execution on the page |
| Guest nav | Inspiration / web capture parks app URL and restores (`parked_url` / `ensure_on_app_origin`) |
| Screenshot path | Inspiration web screenshots use **semaphore(1)** — singleton browser, always serial |
| Isolated browsers | Opt-in only (`PERCEPTION_ALLOW_ISOLATED_BROWSER`) — not the default product path |
| Experiment | `src/run_concurrency_experiment.py` documents risk of concurrent logical sessions |

**Failure mode if agents parallelize browser tools:** URL races, scan/screenshot sequence corruption, guest/app origin interleaving, flaky verify.

### 2.4 What already parallelizes (good news)

| Subsystem | Parallel today | Still serial / slow |
|-----------|----------------|---------------------|
| **Inspiration** | Multi-scout probes, HTTP provider fan-out, blob materialize concurrency, early-cancel | Live viewport screenshots; dribbble/awwwards-style browser-heavy providers (exclusive) |
| **Resources** | `search/executor.py` `asyncio.gather` over providers | Ranking/license after gather; preview blobs; observe_bridge needs browser |
| **Components** | Providers gather per search pass; guidance collectors parallel; shadcn catalog **warm at MCP boot** | Integrate / install; anything that needs live DOM validate |
| **Resolvers** | `SYNC_OFFLOAD` thread pool | N/A |
| **Execution runtime** | Per-tool timeouts/retries | **`BACKGROUND` tier exists but is unused** by live tools; no cross-tool prefetch scheduler |

### 2.5 Prefetch / background today

| Exists | Missing |
|--------|---------|
| Shadcn catalog warm on MCP start | Inspiration scout on `session_start` |
| Health attaches engineering strategy / card | Resource kit prefetch for intent |
| Discover-token / disk caches inside Inspiration | Component shortlist prefetch for unpaid `component` |
| | Cross-family speculative work while first `observe` runs |
| | Cancel-on-episode-end for in-flight prefetch |

---

## 3. Pros of the current architecture

### Speed (partial wins)

- HTTP-heavy families already fan out internally — we are not starting from zero.
- Multi-scout early-cancel returns usable inspiration without waiting for every probe.
- Resolvers stay off the stdio hot path via offload.
- Card + `next` prevents some ritual loops (fewer wasted tool rounds when obeyed).
- Catalog warm amortizes cold component search.

### Reliability

- Clear **single browser ownership** story for production.
- Guest park/restore encodes inspiration-vs-app conflict instead of pretending two browsers.
- Evidence Pack + `implement_blocked` / `claim_ok` protect against blind structural UI.
- Inspiration code explicitly separates HTTP-parallel vs browser-exclusive providers.
- Timeouts/retries are centralized in `execution_runtime`.

### Agent adoption (when it works)

- Face card collapses “what next?” to one tool + args.
- Component face maps to **select foundation**, not plan-only dead ends.
- Spines + short instructions beat loading archive guides.
- Resource gateway + shortcuts share one orchestrator (correct internal shape).

### Correctness / product thesis

- `ok ≠ verified`; pack critical families; class×band subtraction is server-owned.
- Live-12 scorecard + boards (`dev57`) show classify/pack/claim are getting real.
- Parallel browser is correctly treated as a **hard fail** in agent guidance.

---

## 4. Cons / gaps (why it still feels slow or neglected)

### Speed

- **Agent spine is still sequential:** even when inspiration ∥ resources ∥ component could start together, the host only sees `card.next` one tool.
- **No cross-family prefetch** on `session_start` / first structural card — first useful pack still pays full wall clock.
- Browser observe/VF/verify remain multi-second walls (acceptable for truth, but nothing hides behind them yet).
- Inspiration’s valuable path still hits **serial screenshots** on the shared browser.
- Large payloads / full observe detail can dominate latency when agents ignore `summary_only`.

### Reliability

- Browser “one at a time” is **instruction-only** — a host that batches MCP browser tools can still corrupt state.
- Shared Chromium + guest inspiration remains fragile under misuse.
- Prefetch without cancel/budget could thrash APIs or race episode end.

### Agent adoption / tool neglect (core product risk)

- **~75 tools** → most never get called; Resources and Inspiration are easy to skip when not forced by `owed`.
- Adding more tools (or a new `resources` owed family) **worsens** neglect unless hidden behind one call.
- `card.resource` vs Resource Intelligence naming confuses operators and agents.
- Category shortcuts (`_icon_search`, `_font_search`, …) look like separate systems in tools/list.
- BACKGROUND tier unused → long jobs still feel like blocking tools.

### Correctness tradeoffs if we parallelize badly

- Prefetch that navigates the shared browser while the agent observes = corruption.
- Paying “resources” as pack-critical too early = false blockers / ceremony bloat.
- Merging Resource + Component modules = license/stack concerns tangled; harder to reason and test.

---

## 5. Constraints we should treat as invariants

1. **Browser serial per primary session** (default product).  
2. **One agent-facing call per intelligence family** where possible (gateway), parallel **inside**.  
3. **Evidence Pack remains the loop**; don’t invent a second coordination channel.  
4. **Keep Resource Intelligence ≠ Component Intelligence** as code modules.  
5. **Prefetch must be cancelable, budgeted, and episode-scoped.**  
6. **Partial/degraded results > hang** (match Inspiration multi-scout philosophy).  
7. **Do not rely on hosts firing parallel MCP browser batches.**

---

## 6. Option space (for later planning — not decided)

### Option A — Server prefetch only (lowest agent API churn)

On structural `session_start` / when pack remaining includes inspiration/component, start background tasks:

- Inspiration scout (HTTP only; **no** screenshots yet)
- Resource kit (gateway orchestrator, parallel providers)
- Component shortlist (search/select candidates)

Cache on `episode_id`. Later tool calls become cache hits.

| Pros | Cons |
|------|------|
| No new tools; card unchanged | Prefetch waste if agent abandons |
| Hides latency behind observe | Need cancel + budgets |
| Fits Evidence Pack unpaid set | Must never touch shared browser in prefetch |

### Option B — One creative-assets gateway (+ optional attach)

Collapse resource UX to one tool (or attach `creative_kit` onto inspiration/foundation response).

| Pros | Cons |
|------|------|
| Fixes neglect better than pack family | Still need discoverability / card hint |
| Matches “one call” product ask | Category shortcuts become aliases only |
| Parallel providers stay internal | Preview/license still need careful API |

### Option C — Soft parallel hints on the card

`card` exposes `prefetch_ready` / `can_parallel: ["inspiration","component"]` for **non-browser** families — host may call two non-browser tools (if MCP host allows). Browser still serial.

| Pros | Cons |
|------|------|
| Explicit contract | Many hosts still serialize all MCP tools |
| Educational | Easy to misuse if browser listed |

### Option D — Hard browser mutex / queue

Server rejects or queues second browser tool on same `session_id`.

| Pros | Cons |
|------|------|
| Reliability under bad hosts | Latency / surprise errors |
| Makes invariant enforceable | Needs clear `retry_after` UX |

### Option E — Isolated browser pool for inspiration capture

Optional side browsers for screenshots so scout capture doesn’t block app session.

| Pros | Cons |
|------|------|
| True parallel capture | Cost, flaky, against default singleton policy |
| | Ops complexity; keep opt-in |

**Recommended direction for planning (strawman, not approved):**  
**A + B first**, soft docs for C, D if live hosts keep batching, E only if metrics demand it.

---

## 7. Safe parallel classification (planning checklist)

| Class | Examples | Parallel OK? |
|-------|----------|--------------|
| Pure HTTP / API | Resource providers, SERP, component catalogs, license | **Yes** |
| Repo / graph read | resolve_*, design_graph summary, UX KB | **Yes** (offload) |
| Coordinator mutate | portfolio pay, episode update | Serialize per episode or merge carefully |
| Browser app session | navigate, observe, verify, VF, probes | **No** (per primary session) |
| Browser guest | inspiration screenshot, some gallery providers | **No** on shared browser; optional isolated pool later |
| Hybrid | `resource_observe_bridge`, live design snapshot | Treat as browser-bound |

---

## 8. Metrics to define before implementation

| Metric | Why |
|--------|-----|
| `session_start` → first usable inspiration pack (p50/p95) | Prefetch payoff |
| `session_start` → foundation select usable (p50/p95) | Component cold path |
| Resource gateway wall time vs provider count | Fan-out efficiency |
| Cache hit rate for prefetch | Waste vs win |
| Browser tool overlap / race incidents | Need for hard mutex |
| Tool call mix (% Resources / Inspiration / Component) | Neglect |

Existing references: `docs/PERFORMANCE_TOOL_CLASSIFICATION.md`, Inspiration concurrent plan docs, `run_concurrency_experiment.py`.

---

## 9. Risks to call out in any implementation plan

1. **Prefetch cost** — API keys, rate limits, wasted scouts.  
2. **Episode lifecycle** — session_end must cancel in-flight work and drop caches.  
3. **Wrong family prefetch** — hotfix must not warm inspiration gallery. Honor pack/class.  
4. **Name collision** — rename or document `card.resource` vs Resource Intelligence before teaching agents.  
5. **Host limits** — Cursor may not run true parallel MCP tools; design must win even when host is serial.  
6. **Scope creep** — merging intelligences or adding pack-critical `resources` too early.

---

## 10. Suggested planning phases (after approval)

| Phase | Scope | Exit criteria | Status |
|-------|--------|----------------|--------|
| **P0 — Spec** | Lock invariants; classify tools; decide A/B/C | Written plan + non-goals | Done (this doc) |
| **P1 — Prefetch** | Episode-scoped HTTP prefetch for unpaid inspiration/component/resource-kit; budgets; cancel | Latency metrics improve; hotfix stays lean | **Shipped** — `episode_prefetch.py` (heavy+ only; `PERCEPTION_EPISODE_PREFETCH`) |
| **P2 — Gateway UX** | One creative-assets entry; shortcuts as aliases; optional kit on inspiration/foundation response | Resource call rate up without new owed family | **Shipped** — `perception_creative_assets` + kit attach on collect |
| **P3 — Card hints** | Optional `prefetch_ready` / non-browser parallel hint | Docs + boards; no browser in parallel set | **Shipped** — `card.prefetch` / `card.can_parallel` / `card.spine` |
| **P4 — Enforce** | Optional browser single-flight queue if races persist | Concurrency experiment green under abuse | **Shipped** — `browser_flight.py` (queue default; `PERCEPTION_BROWSER_LOCK`, `_MODE=reject`, `_WAIT_S`) |

---

## 11. Open questions (resolve in planning)

1. Prefetch trigger: every `session_start`, or only when `evidence_band ∈ {heavy, very_heavy}`?  
   → **Resolved:** heavy / very_heavy only; hotfix/forms never warm gallery.  
2. Should creative-assets attach to inspiration collect, foundation select, or both?  
   → **Resolved (v1):** attach kit on inspiration collect when prefetch ready.  
3. Do we ever put `resources` in pack.phases as **optional** (`resources?`) without making it critical?  
   → **Resolved (v1):** `resources?` on greenfield/redesign heavy+; portfolio unpaid nudge; multi-category creative_kit prefetch (font/pattern/gradient/icon + illustration/animation). Not claim-critical.  
4. Hard browser mutex now or after measuring host batching?  
   → **Resolved:** process-wide primary-browser flight lock (queue+timeout default; reject mode optional).  
5. Rename `card.resource` → `card.spine` / `card.guide` to kill the collision?  
   → **Resolved (v1):** added `card.spine` alias; `resource` kept for compat (still means methodology URI).  
6. What is the max wall budget for prefetch (e.g. 2s soft / 5s hard cancel)?  
   → **Resolved:** soft 2s (docs), hard 5s per family (`PERCEPTION_PREFETCH_HARD_S`).

---

## 12. Key files (implementation map)

| Area | Paths |
|------|--------|
| Tools / catalog | `src/navigation/mcp/tools.py`, `tool_catalog.py`, `instructions.py` |
| Executor / tiers | `src/navigation/execution_runtime/executor.py`, `policies/tier.py`, `timeout.py` |
| Browser ownership | `visual_browser_intelligence/browser/browser_session_manager.py`, `session_store.py` |
| Face / pack | `coordination_intelligence/planning/coordinator_card.py`, `evidence_pack.py`, `episode_portfolio.py` |
| Bridge | `coordination_intelligence/integration/bridge.py` |
| Inspiration parallel | `inspiration_intelligence/multi_scout.py`, `concurrent.py`, `web_inspire.py` |
| Resource parallel | `resource_intelligence/search/executor.py`, `planning/orchestrator.py` |
| Component parallel | `component_intelligence/search/executor.py`, `providers/manager.py` |
| Perf notes | `docs/PERFORMANCE_TOOL_CLASSIFICATION.md` |

---

## 13. Bottom line

**Pros:** Strong separation of concerns, real internal parallelism in Inspiration/Resources/Components, clear browser ownership story, Evidence Pack giving agents a single loop.

**Cons:** Speed is still limited by **sequential agent-facing calls** and **no cross-family prefetch**; reliability of browser seriality is **policy-not-enforced**; **tool sprawl** causes Resource (and other) neglect; BACKGROUND/prefetch machinery is underused.

**Plan implication:** Optimize for **server-side parallel + one-call gateways + episode prefetch**, not for “agents fire five MCP tools at once,” and not for merging Resource into Component.
