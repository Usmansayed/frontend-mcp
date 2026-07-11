# Figma Intelligence — Architecture

**Status:** Architecture scaffold (v0.1) — no execution pipeline wired yet.

## Mission

Figma Intelligence is **not** a wrapper around Figma Console MCP. It is an orchestration and intelligence layer inside Frontend Perception MCP. External MCPs are execution providers only when the pipeline reaches the provider stage.

**Our MCP remains the brain.**

## Pipeline

```text
Agent
  │
  ▼
FigmaIntelligenceService
  │
  ├─ intent/                  → parse agent goal
  ├─ planning/                → provider routing + intelligence hints
  ├─ community_intelligence/  → ⭐ query expansion (synonyms, styles, industries, components)
  ├─ discovery/               → execute ranked community searches via providers
  ├─ candidate_intelligence/  → ⭐ normalize rich CandidateProfile metadata
  ├─ ranking/                 → score using profile (not keywords alone)
  ├─ providers/               → thin execution only (Figma Console last)
  ├─ extraction/              → snapshot, components, tokens (post-provider)
  ├─ evaluation/              → Design Sense, Consistency, Component, Framework
  └─ registry/                → Reference Registry + PDG bridge
  │
  ▼
Agent
```

## Multi-intelligence participation

| Stage | Modules |
|-------|---------|
| **Before provider** | Framework, Component, Design Sense, Consistency → search hints |
| **After extraction** | Same modules → quality, fit, reusability, compatibility, inspiration score |

Providers return **raw design data**. Intelligence modules decide value.

## Provider interface

All providers implement `FigmaProvider` (`providers/protocol.py`):

- `discover_candidates(plan, intent)` → community/file candidates
- `extract_design(candidate, intent)` → tokens, components, variables
- `health()` → degraded reporting

**First provider:** `figma_console` (southleft/figma-console-mcp)  
**Second provider:** `official_figma` (https://mcp.figma.com/mcp)  
**Future:** Figwright, community MCPs, REST adapters

Providers are swappable — pipeline stages do not change when adding a provider.

## Ecosystem integration

```text
Figma Community
  → Discovery
  → Extraction
  → Design Snapshot (design_snapshot_engine)
  → Component DNA / Patterns
  → Reference Registry (design_reference_registry)
  → Project Design Graph (consistency_intelligence)
  → Design Sense / Consistency / Component Intelligence
```

**Relationship to Consistency Intelligence:**  
`consistency_intelligence/discovery/sources/figma.py` is a thin PDG ingestor for pre-extracted token payloads. Figma Intelligence **orchestrates** discovery and extraction; CI **consumes** normalized knowledge via the graph.

## Package layout

```text
figma_intelligence/
├── providers/              # protocol + manager + figma_console | official_figma | future
├── intent/                 # agent goal parsing
├── planning/               # search planner + orchestrator
├── community_intelligence/ # ⭐ query expansion before any provider call
├── candidate_intelligence/ # ⭐ CandidateProfile normalization
├── discovery/              # execute community plan via providers
├── ranking/                # profile-aware ranking
├── extraction/             # provider extraction (after brains)
├── evaluation/             # multi-intelligence review
├── registry/               # reference registry bridge
├── adapters/               # ecosystem hints + snapshot normalization
├── models.py
├── service.py
└── docs/
```

## MCP tools (planned)

| Tool | Purpose |
|------|---------|
| `perception_figma_discover` | Intent → plan → candidates (no extraction) |
| `perception_figma_pipeline` | Full pipeline through extraction + evaluation |
| `perception_figma_providers` | List provider capabilities + health |

Not registered until execution phase — scaffold only.

## Phase plan

1. **Architecture + research** — models, protocol, stubs, docs ✅
2. **Community Intelligence** — multi-pass query expansion ✅
3. **Candidate Intelligence** — `CandidateProfile` normalization ✅
4. **Provider wiring** — Figma Console MCP (**after** brains; not started)
5. **Extraction + snapshot** — Design Snapshot Engine integration
6. **Multi-intelligence evaluation** — contract-based scoring from sibling modules
7. **Reference Registry + PDG** — persist valuable extractions

## Related

- [RESEARCH.md](./RESEARCH.md) — external tooling survey
- [PIPELINE.md](./PIPELINE.md) — stage contracts
- [../../../docs/features/figma_intelligence.md](../../../docs/features/figma_intelligence.md) — platform feature doc
