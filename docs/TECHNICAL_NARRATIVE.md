# Technical Narrative — How We Build Frontend Perception

This document is for the **landing page technical section**, investor conversations, and README “architecture” tabs. It explains **how we think**, **how systems connect**, and **why the design is creative** — not a feature checklist.

Pair with [PRODUCT_STORY.md](./PRODUCT_STORY.md) for marketing copy.

---

## The one idea behind everything

> **We orchestrate intelligence. We don’t hoard it.**

Most tools either:

- **Dump raw data** (console logs, network HAR, screenshots) and hope the LLM figures it out, or  
- **Embed an LLM** in the server and become expensive, flaky, and untestable.

We chose a third path:

```text
External worlds (234 registries, official docs, Lighthouse, CRG, CDP)
        ↓
Adapter + normalize + cache
        ↓
One stable contract the agent can reason over
        ↓
Host agent (Cursor / Claude) decides what to do next
```

Every major subsystem follows this shape. That repetition is the technical beauty — **one platform pattern, eight domains**.

---

## Platform pattern: thin MCP, thick modules, fat providers

```text
┌─────────────────────────────────────────────────────────┐
│  MCP layer (navigation/mcp/)                            │
│  tools.py + handlers.py — schema in, envelope out       │
│  NO domain logic                                        │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  Intelligence module (service.py facade)                │
│  models · cache · registry · orchestration              │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  Providers (pluggable externals)                        │
│  Grounded Docs · shadcn registries · CRG · Lighthouse   │
└─────────────────────────────────────────────────────────┘
```

**Creative choice:** Handlers never import Grounded Docs, shadcn URLs, or Lighthouse directly. Modules expose `service.py`; providers swap without breaking the MCP contract. Context7 became Grounded Docs with **zero handler changes** — only the adapter layer moved.

---

## The agent loop we encode in architecture

We don’t just document “observe → verify” in `AGENT_GUIDE.md`. The **tool graph** is designed around it:

| Phase | Tools | Design intent |
|-------|-------|---------------|
| Bootstrap | `health`, `session_start` | Fail fast if dev server down |
| Observe | `navigate_and_observe`, `observe` | Facts + `scan_id` + inline images |
| Reason | `code_context`, `framework_docs`, `plan_component_search` | Connect UI ↔ code ↔ docs ↔ components |
| Act | repo edits + `execute_script` / `execute_actions` | Agent edits source; MCP runs deterministic scripts |
| Verify | `verify` | Hard gate — auto failure screenshot |
| Regression | `diff` | Two `scan_id`s → text + visual heatmap |
| Quality | `full_diagnosis`, `debug_mode`, `audit_mode` | Composed reports, not log dumps |

**Creative choice:** `perception_verify` on failure **automatically re-observes** and attaches the failure screenshot. The agent doesn’t have to remember — the contract teaches good behavior.

---

## Component Intelligence — universal search engine (and what comes after)

This is the flagship “we built something real” story for the landing page.

### The problem we refused to solve the naive way

A naive component MCP would:

1. Clone 234 shadcn registries into a local database  
2. Reindex weekly  
3. Ship stale components forever  
4. Break when registries rename `navbar` → `navigation-menu`

**We refused.** No local component registry. No forked component source. **Intelligence in planning and execution, not in storage.**

### Phase 2 — Synthesis & selection (scaffold)

Structured guidance from all modules → `guidance/synthesis.py` → priority-based ranking (no fixed weights).

### Phase 3–5 — Integration pipeline (scaffold)

`IntegrationPipeline`: Documentation Reader → Installation Planner → Dependency Resolver → Compatibility Resolver → Installer → Component Adapter → Browser Validator → Repair Loop (`fix_planner` consults modules on failure).

See [features/component_intelligence_architecture.md](./features/component_intelligence_architecture.md).

### Phase 1 — Universal search (shipped)

```text
"Modern glass dashboard navbar"
        ↓
┌───────────────────┐
│  Query Parser     │  lexicon: component types, styles, theme,
│                   │  page context (dashboard, SaaS), animations
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Search Planner   │  primary intent · synonyms · style→registry affinity
│  (deterministic)  │  planned_queries[] with confidence + pass_number
└─────────┬─────────┘     OR host agent passes search_plan override
          ↓
┌───────────────────┐
│  Multi-pass       │  Pass 1: primary ("navbar", "glass navbar")
│  Executor         │  Pass 2: expanded ("navigation menu", "menubar")
│                   │  Pass 3: broad ("layout", "shell")
│                   │  Stop when: 8+ good hits from 3+ registries
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Parallel         │  asyncio.gather per provider per pass
│  Provider Search  │  12 concurrent catalog fetches (cached)
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Provider-aware   │  @shadcn ← "navigation-menu", "menubar"
│  vocabulary       │  @aceternity ← "navbar", "floating-navbar"
│                   │  @tailark ← "header"
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Normalize        │  ComponentCandidate — same schema everywhere
│  + Smart Merge    │  dedupe by id, keep best score, track sources[]
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Search Session   │  session_id, passes, queries, latency per pass
└───────────────────┘
```

**Creative details worth showcasing:**

1. **Split planner brain** — MCP builds a deterministic plan; the host agent *may* refine via `perception_plan_component_search` → `search_plan` JSON. LLM strategy without LLM in the server.

2. **Registry diversity gate** — We don’t stop at “13 Aceternity navbars scored 1.0.” Sufficiency requires **breadth across registries**, forcing pass 2 to surface `@shadcn` `navigation-menu` and `@tailark` `header`.

3. **Built-in `@shadcn` injection** — The core UI catalog isn’t in `registries.json`. We inject `ui.shadcn.com/r/styles/new-york/registry.json` when the index omits it. Pragmatic, not dogmatic.

4. **Per-registry query filtering** — Same search plan, different words sent to each provider. Universal search that respects local dialect.

5. **Search session as flight recorder** — Every query is debuggable: which pass, which term, which registry, how many ms. Built for tuning retrieval quality over time.

6. **Group A + Group B providers** — One `ComponentProvider` protocol; shadcn ecosystem live; MUI/Chakra/Mantine placeholders ready. Universal search engine, not “shadcn MCP.”

### Phase 2 — Ranking (planned)

Raw relevance score isn’t enough. Next: rank candidates with **project context**:

- Design Sense signals (motion-heavy query → prefer Magic UI / Aceternity)
- Detected stack (Next App Router, Tailwind v4, existing registries in `components.json`)
- Consistency hints (token compatibility)

**Principle:** Ranking consumes other modules; Component Intelligence doesn’t become a monolith.

### Phase 3 — Adaptation (planned)

Found the right component? Still not done — it must **fit your repo**:

```text
ComponentCandidate
        ↓
Read project structure (paths, aliases, cn utility, theme)
        ↓
Transform install paths, imports, token classes
        ↓
AdaptedComponentPatch (files + diff preview)
        ↓
Agent reviews → applies
```

**Creative framing:** Search finds *what*; adaptation produces *how it lands in your codebase*. Still deterministic transforms where possible; agent approves.

### Phase 4 — Installation (planned)

`provider.install(component_id)` already on the protocol — wire to `npx shadcn@latest add`, verify with `perception_observe`, regression with `perception_diff`.

**Full story for landing page:**

> **Discover → Rank → Adapt → Install → Verify**  
> One module, four phases, zero local component database.

---

## Framework Intelligence — we don’t know React, we detect it

Another orchestration story.

```text
package.json + lockfiles + configs + folders
        ↓
Framework Detector (zero framework doc knowledge)
        ↓
Project Metadata { react, 19.0, vite, pnpm, typescript, … }
        ↓
DocumentationProvider (Grounded Docs today)
        ↓
Adapter: registry → library_id, query_builder → enriched search
        ↓
search → miss? → scrape on demand → search again
        ↓
Normalize → FrameworkKnowledgeResponse
        ↓
Cache key: framework:version:topic_hash
```

**Creative splits:**

| Layer | Knows framework? | Job |
|-------|------------------|-----|
| Detector | No — only reads files | Facts from disk |
| Adapter registry | Yes — npm → doc URL | Routing |
| MCP handlers | No — only normalized shape | Stable contract |

Swap Context7 → Grounded Docs by changing **adapter folder**, not the agent integration.

**Cross-platform creativity:** Windows `npx.cmd` resolution, PATH augmentation when IDE strips Node, UTF-8 subprocess, Node 22+ gate, graceful `degraded[]` when CLI unavailable — detector still works offline.

---

## Frontend Quality — composition, not concatenation

Console, network, audits, and visual insights are **separate modules**. Reports **orchestrates**:

```text
perception_full_diagnosis
    ├── observe (visual + DOM + dev_insights)
    ├── console_get (CDP ring buffer since session start)
    ├── network_get (failures, slow, API groups, HAR path)
    ├── audit_accessibility + audit_performance (Lighthouse)
    └── assemble PerceptionReport
            ├── blocking (first)
            ├── warnings
            ├── suggested_fixes (rule-based only — no LLM prose)
            └── artifacts[] → scan resources
```

**Creative ADR:** Lighthouse runs in a **dedicated Chrome**, not the managed Browser Use session — avoids CDP hub disruption. Same URL, isolated browser, stable session for the agent’s work.

**Network creativity:** Reports prioritize failures → API → slow → asset noise. Duplicate detection (same URL within 2s). GraphQL `operationName` heuristic. HAR 1.2 per scan as MCP resource.

**Console creativity:** One CDP hub, multiple collectors fan-in. Full session history from `session_start`, not just the last observe window.

---

## Visual & Browser — `scan_id` as the artifact hub

Every observation is a **moment in time** with a stable ID:

```text
scan_id
 ├── screenshot.png / screenshot-annotated.png
 ├── network.har
 ├── diagnosis.json / diagnosis.md
 ├── lighthouse-*.json
 └── embedded perception_report
```

**Creative choice:** Inline `ImageContent` in MCP tool responses *and* persistent resources. Agents see images immediately; humans deep-link later.

Visual diff: structural text diff + side-by-side PNG + heatmap — three lenses on the same regression.

---

## Codebase Intelligence — optional graph, mandatory browser

CRG behind `ICodeGraph`. Browser never blocks on graph build.

```text
perception_code_context
        ↓
semantic_search_nodes / query_graph
        ↓
component files, routes, button candidates
        ↓
Agent edits file → perception_verify on live UI
```

**Creative framing:** Code graph is **navigation hints for the brain**, not a required pipeline stage. CRG down? Browser still runs.

---

## Figma Intelligence — connection + coordination (v2)

Figma Intelligence is **not** another design engine. It connects the user's Figma account to Frontend Perception MCP via **southleft/figma-console-mcp** and returns **normalized design context** for sibling modules.

```text
User → perception_figma_connect (PAT)
        ↓
Connection Manager → Session Manager → Console MCP Adapter
        ↓
Context Normalizer → Design Cache → Coordination Layer
        ↓
FigmaDesignContext → Agent → Design Sense / Consistency / Components / …
```

**Creative choices:**

1. **Orchestrate, don't reimplement** — All Figma API/MCP tool names stay inside the adapter.

2. **Connect once** — PAT stored locally; session tracks file, page, frame, selection.

3. **Cache intelligently** — TTL cache keyed by session; `refresh` bypasses when context may have changed.

4. **Legacy pipeline retained** — Community discovery/ranking remains for backward compatibility; new workflows use connect + context only.

See [features/figma_intelligence.md](./features/figma_intelligence.md) and ADR-026.

---

## Design Sense vs Consistency — two kinds of “good”

We split what others merge:

| Question | Module | Method |
|----------|--------|--------|
| Is this good UX? | Design Sense | Heuristics, overflow, overlaps, hierarchy reasoning |
| Does this match the system? | Consistency | Token math, spacing scales, radii, state parity |

**Future Consistency pipeline:**

```text
code tokens + computed styles + screenshot
        ↓
rule validators (spacing, type, color, states)
        ↓
ConsistencyReport (severity, expected vs actual, locations)
        ↓
optional fix patches → agent applies
```

**Creative choice:** UX coaching and design-system enforcement are different failure modes. Separate modules → separate tests → separate MCP tools.

---

## Envelope contract — every tool speaks one language

```json
{
  "contract_version": "1.0",
  "tool": "perception_search_components",
  "ok": true,
  "scan_id": "...",
  "degraded": [],
  "data": { ... },
  "agent_summary": { "blocking": [], "advisory": [] }
}
```

Agents learn once. Contract tests lock it. `degraded[]` explains partial failure without lying `ok: true` silently.

---

## The full platform flywheel (one agent session)

Landing page diagram material:

```text
User: "Build a SaaS pricing page with glass navbar"

1. perception_detect_framework     → React 19, Vite, Tailwind
2. perception_framework_docs       → real useEffect / form patterns
3. perception_plan_component_search → navbar + glass + dashboard plan
4. perception_search_components    → multi-pass → ranked candidates
   (future: adapt + install)
5. Agent writes JSX in repo
6. perception_navigate_and_observe → scan_id, blocking check
7. perception_verify               → text + URL criteria
8. perception_full_diagnosis       → ship-ready report
   (future: perception_consistency_audit)
9. perception_diff                 → regression on next edit
```

**One MCP. Intelligence modules. One loop.** Each step uses a different module; the agent never leaves the protocol.

---

## What we explicitly don’t do (credibility)

| Anti-pattern | Our choice |
|--------------|------------|
| Chrome extension + middleware | Managed CDP session |
| LLM inside MCP for “fixes” | Rule-based hints; agent writes code |
| Local component registry | Live orchestration across registries |
| Monolithic “browser tool” | Modular intelligence modules |
| Autonomous Browser Use as default | Host agent is primary; Browser Use is runtime |
| Copy inactive BrowserTools deps | Study clone, reimplement on our schema |

---

## Landing page — “Technical beauty” copy blocks

### Section: Universal component search

**Headline:** A search engine, not a component database.

**Body:** We don’t mirror 234 registries. We parse intent, expand terminology across three passes, speak each registry’s native vocabulary, fetch catalogs in parallel, and merge results into one normalized schema — with a full session log for every query. The agent can override the plan; the server stays deterministic.

### Section: Provider architecture

**Headline:** Plug in worlds. Ship one contract.

**Body:** Framework docs, component registries, code graphs, Lighthouse, and CDP all enter through provider interfaces. Adapters normalize; caches key by version; handlers stay dumb. When upstream changes, we swap a folder — not the product.

### Section: Verify-first frontend

**Headline:** Facts before “done.”

**Body:** Every observe returns blocking issues first. Verify failures attach screenshots automatically. Diff connects two scan IDs across text and pixels. Diagnosis composes console, network, audits, and visual signals into one report — no LLM narration in the server.

### Section: Built for agents

**Headline:** Your model is the brain. We are the runtime.

**Body:** Playbooks in `AGENT_GUIDE.md`. Tools return structured `agent_summary`, not prose suggestions. Auth gates stop for humans. Form probes precede blind fills. The MCP is testable, cacheable, and cheap to run at scale.

### Section: Roadmap honesty

**Shipped:** Search Phase 1, framework detection + Grounded Docs, full quality stack, modular intelligence layout.

**Next:** Figma Intelligence provider wiring. Component ranking → adaptation → install. Consistency validators. Token snapshots across code and DOM. SEO Intelligence Phase 1 (GSC + GA4 OAuth).

### Section: SEO Intelligence (architecture_v1)

**Headline:** We are not Ahrefs. We orchestrate your data.

**Body:** SEO Intelligence gathers user-owned Search Console and GA4 evidence, technical crawl from LibreCrawl (local), Lighthouse CWV, and Browser Intelligence rendering signals. Everything normalizes into an SEO Knowledge Graph. Cross-analysis explains *why* indexing or CTR fails — with `evidence_ids` on every recommendation. Verify loop matches frontend: analyze → fix → `perception_verify` → re-audit.

**Explicit non-goals:** keyword databases, backlink crawlers, SERP scrapers, internet-scale crawlers.

---

## Glossary (for landing FAQ)

| Term | Meaning |
|------|---------|
| **Orchestrate** | Call external sources live; normalize; don’t own the data |
| **Search plan** | Ordered queries + metadata; deterministic or agent-supplied |
| **Search session** | Flight recorder for one component search |
| **Provider** | Pluggable backend behind a module protocol |
| **Adapter** | Translates upstream (Grounded Docs, registries) to our models |
| **scan_id** | Artifact hub for one browser observation |
| **blocking** | Must fix before ship (errors, 4xx, exceptions) |
| **degraded** | Partial success; tool explains what’s missing |
| **Group A / B** | Shadcn ecosystem vs MUI/Chakra-style external libraries |

---

## Related

- [PRODUCT_STORY.md](./PRODUCT_STORY.md) — marketing copy source  
- [architecture.md](./architecture.md) — system overview  
- [INTELLIGENCE_MODULES.md](./INTELLIGENCE_MODULES.md) — module map  
- [features/component_intelligence.md](./features/component_intelligence.md) — search engine detail  
- [design_decisions.md](./design_decisions.md) — ADRs  

---

*Update this doc when a new phase ships (ranking, adaptation, consistency validators) so the landing page story stays honest and ambitious.*
