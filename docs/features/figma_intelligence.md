# Figma Intelligence

**Path:** `src/navigation/figma_intelligence/`  
**Status:** Account-scoped scaffold — Community duplication + Figma Console extraction

> **Public inspiration** (Dribbble, Behance, etc.) lives in [inspiration_intelligence.md](./inspiration_intelligence.md). This module is for the **user's own Figma account** — files, components, variables, and design systems.

## What it is

Figma Intelligence connects to the user's Figma account and converts **owned design files** into **structured design knowledge** the rest of the platform can reuse. It is an orchestration layer — not another MCP, not a Figma Console wrapper.

```text
Agent → Intent → Community Intelligence → Community Discovery (no PAT)
      → Candidate Intelligence → Ranking → Selection Planner
      → Figma Console MCP (PAT) → Extraction → Deep Candidate Review
      → Reference Registry → Project Design Graph → Agent
```

**Architecture frozen v1** — see `figma_intelligence/docs/ARCHITECTURE_FROZEN.md`.

## What it is not

| Anti-pattern | Our approach |
|--------------|--------------|
| Wrapper around Figma Console MCP | Console is one **provider** behind `FigmaProvider` protocol |
| Separate MCP server | Lives inside Frontend Perception MCP |
| Autonomous Figma editor | Read/extract only in v1 |
| UX critique | Design Sense Intelligence |
| Token drift enforcement | Consistency Intelligence |

## Capabilities

| Capability | Status |
|------------|--------|
| Intent parsing (inspire, extract DS, compare, reuse, learn) | ✅ |
| Search planning with multi-intelligence hints | ✅ |
| Community Intelligence (synonym/style/industry/component expansion) | ✅ |
| Candidate Intelligence (`CandidateProfile` metadata) | ✅ |
| Profile-aware ranking | ✅ |
| Selection Planner (budget-aware retrieval) | ✅ |
| Deep Candidate Review (post-extraction scoring) | ✅ |
| Community Discovery Adapter (public search, no PAT) | ✅ |
| Figma Console MCP (extraction only, PAT) | ✅ wired |
| Architecture frozen v1 | ✅ |
| Live extraction (requires `file_key` + PAT/bridge) | 🚧 |
| Reference Registry + PDG ingest | 📋 planned |
| MCP tools | 📋 planned |

## Providers

| ID | Backend | Best for |
|----|---------|----------|
| `figma_console` | southleft/figma-console-mcp | Community search, DS kit, DTCG export |
| `official_figma` | mcp.figma.com | Owned files, org libraries, Code Connect |
| `future` | Figwright, REST, community MCPs | TBD |

## Ecosystem role

Long-term knowledge flow:

```text
Figma Community → Discovery → Extraction → DesignSnapshot
  → Component DNA → Patterns → Reference Registry → Project Design Graph
  → Design Sense / Consistency / Component Intelligence
```

## MCP tools (planned)

- `perception_figma_discover` — candidates without extraction
- `perception_figma_pipeline` — full pipeline
- `perception_figma_providers` — provider health + capabilities

## Module docs

- [ARCHITECTURE.md](../src/navigation/figma_intelligence/docs/ARCHITECTURE.md)
- [RESEARCH.md](../src/navigation/figma_intelligence/docs/RESEARCH.md)
- [PIPELINE.md](../src/navigation/figma_intelligence/docs/PIPELINE.md)

## Related modules

- **Design Workflow Intelligence** — multi-step design tool workflows (complementary)
- **Consistency Intelligence** — consumes extracted tokens via PDG (`discovery/sources/figma.py`)
- **Design Reference Registry** — stores reference snapshots from extractions
- **Component Intelligence** — parallel orchestration pattern (providers + planning)
