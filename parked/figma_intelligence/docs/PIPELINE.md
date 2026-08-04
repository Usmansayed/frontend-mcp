# Figma Intelligence — Pipeline stages

## Stage 1: Intent (`intent/parser.py`)

**Input:** `query`, optional `FigmaIntentKind`, `repo_root`  
**Output:** `FigmaIntent`

## Stage 2: Search planning (`planning/search_planner.py`)

**Input:** `FigmaIntent`  
**Output:** `FigmaSearchPlan` — provider routing + Framework/Component hints only.

Query expansion is **not** here — see Community Intelligence.

## Stage 3: Community Intelligence (`community_intelligence/planner.py`) ⭐

**Input:** `FigmaIntent`, `FigmaSearchPlan`  
**Output:** `CommunitySearchPlan`

Responsibilities:

- Expand one query into many semantic searches (multi-pass, like Component Intelligence)
- Page synonyms (`dashboard` → `admin panel`, `analytics`, `control center`)
- Style expansion (`minimal`, `glassmorphism`, `bento`, design languages like Linear/Vercel)
- Component expansion (`dashboard` → `sidebar`, `table`, `chart`, `card`)
- Industry expansion (`saas`, `fintech`, `crm`, `e-commerce`)
- Rank queries by confidence; mark `execute=True` above threshold

## Stage 4: Discovery (`discovery/community.py`)

**Input:** `FigmaSearchPlan`, `CommunitySearchPlan`, providers  
**Output:** raw `FigmaCandidate[]`

Executes `executable_queries` via provider chain. Providers remain thin.

## Stage 5: Candidate Intelligence (`candidate_intelligence/`) ⭐

**Input:** raw candidates from discovery  
**Output:** candidates with `CandidateProfile`

Profile fields:

| Field | Purpose |
|-------|---------|
| `industry` | SaaS, fintech, CRM, … |
| `page_type` | dashboard, landing, auth, … |
| `components` | sidebar, table, chart, … |
| `framework` | react, shadcn, … |
| `style` | minimal, glass, bento, … |
| `design_language` | linear, vercel, stripe, … |
| `complexity` | simple / moderate / complex |
| `patterns` | bento_grid, sidebar_layout, … |
| `confidence` | metadata inference strength |

Sibling modules score candidates **without reopening** Figma files.

## Stage 6: Ranking (`ranking/ranker.py`)

Profile-aware scoring — who is **best**.

## Stage 7: Selection Planner (`selection/planner.py`) ⭐

Budget-aware retrieval — who is **worth opening**.

- Batch 1: top 3 immediately
- Batch 2: next 5 if confidence below threshold
- Deduplicate same design system family
- Respect `max_api_calls` rate budget

## Stage 8: Provider + Extraction (`providers/figma_console/`)

Figma Console MCP (southleft) — thin execution only.

## Stage 9: Deep Candidate Review (`review/deep_review.py`) ⭐

Score **extracted** tokens/components — Design Sense, Consistency, Component, Framework.

## Stage 10: Registry (`registry/reference_bridge.py`)

Reference Registry + PDG ingest when valuable.

## Facade (`service.py`)

| Method | Stages |
|--------|--------|
| `discover()` | 1–7 (through selection planning) |
| `run_pipeline()` | 1–10 |

See [ARCHITECTURE_FROZEN.md](./ARCHITECTURE_FROZEN.md) — **pipeline frozen v1**.
