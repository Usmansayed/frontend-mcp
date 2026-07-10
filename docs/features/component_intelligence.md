# Component Intelligence — Search Engine (Phase 1)

**Status:** Phase 1 search shipped · [Complete architecture](./component_intelligence_architecture.md)  
**Module:** `src/navigation/component_intelligence/`

> Search is ~10% of Component Intelligence. See **[component_intelligence_architecture.md](./component_intelligence_architecture.md)** for the full orchestration pipeline: foundation selection, integration engine, browser validation, and repair loop.

## Goal

Orchestrate component discovery across multiple providers. **No local component registry** — we do not store component source code.

Intelligence lives in **search planning** and **multi-pass execution**, not in maintaining our own index. The host agent (LLM) may refine plans; the MCP server builds deterministic plans and runs provider searches.

## Pipeline

```text
User Query
    ↓
Query Parser (rich lexicon)
    ↓
Search Planner (intent, synonyms, provider vocabulary)
    ↓
Multi-pass Search Executor
    ↓
Parallel Provider Search (per pass)
    ↓
Smart Merge + Dedupe
    ↓
Search Session + Candidate List
```

## Search planner

For every query the planner produces:

| Field | Purpose |
|-------|---------|
| `primary_intent` | Condensed goal (component + context + style) |
| `component_types` | navbar, pricing, login, … |
| `alternative_terminology` | navigation menu, header, menubar, … |
| `style_keywords` | modern, glassmorphism, … |
| `theme` | dark / light |
| `page_context` | dashboard, landing page, auth, … |
| `suggested_registries` | Registry namespaces ranked by style/intent affinity |
| `planned_queries` | Ordered queries with `confidence` and `pass_number` |

**Passes:**

1. **Primary** — raw query + component + style composites  
2. **Expanded** — synonyms and provider-aware terminology  
3. **Broad** — layout/marketing concepts when results are still weak  

The executor stops early only when there are enough high-scoring candidates **across multiple registries** (default: 8+ at score ≥ 0.35 from ≥ 3 registries).

## Provider-aware vocabulary

`planner/provider_vocabulary.py` maps registry namespaces to preferred naming:

- `@shadcn` → `navigation-menu`, `menubar`, `breadcrumb`
- `@aceternity` → `navbar`, `floating-navbar`
- `@tailark` → `header`, `navbar`

Providers receive only the plan terms relevant to their vocabulary. The core `@shadcn` UI registry is injected when absent from the public registries index.

## Query parser

Extracts from natural language:

| Field | Examples |
|-------|----------|
| `component_types` | button, card, navbar, pricing |
| `page_types` | login form, pricing section |
| `page_context` | dashboard, auth, saas |
| `styles` | modern, glassmorphism |
| `animations` | animated, motion |
| `audience` | saas, enterprise |
| `theme` | dark, light |
| `search_hints` | merged hints for provider scoring |

Extend `parser/lexicon.py` for new styles and contexts.

## Search session

Every search records:

- `session_id`, `original_request`
- `passes_executed`, `queries_executed`
- `providers_searched`, `results_per_provider`
- `latency_ms` per pass and total

Returned in `component_search.search_session` for debugging and tuning.

## Merged candidates

Duplicates (same `id`) are merged. Metadata tracks:

- `matched_query`, `search_pass`, `plan_confidence`
- `sources` — additional provider/query hits for the same item

## Provider groups

### Group A — Shadcn registry ecosystem (`shadcn_ecosystem`)

Unified provider over the [shadcn registries index](https://ui.shadcn.com/r/registries.json) plus the built-in `@shadcn` UI catalog.

### Group B — External providers (`external`)

Placeholder adapters (disabled until integrated): MUI, Chakra UI, Mantine, Flowbite, HeroUI, Park UI, Tremor, Melt UI, Web Awesome, React Aria.

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_plan_component_search` | Build search plan only (no provider calls) |
| `perception_search_components` | Plan → multi-pass search → merged candidates |

Optional `search_plan` on `perception_search_components` lets the host agent override or refine the deterministic plan.

## Tests

- `tests/test_component_search.py` — parser, planner, merge, scoring
- Live search requires network access to shadcn registries

## Related

- [INTELLIGENCE_MODULES.md](../INTELLIGENCE_MODULES.md)
- [tool_reference.md](../tool_reference.md)
