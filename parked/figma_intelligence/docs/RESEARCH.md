# Figma Intelligence — Research

Research completed before implementation. Sources surveyed July 2026.

## 1. Figma Console MCP (southleft)

**Repo:** [github.com/southleft/figma-console-mcp](https://github.com/southleft/figma-console-mcp)

| Aspect | Notes |
|--------|-------|
| **Role for us** | First **execution provider** — not the product |
| **Modes** | Local (~106 tools), Cloud (~95), Remote (~9) |
| **Strengths** | Desktop Bridge plugin, design system kit, variables, DTCG token export, screenshots, component metadata |
| **Community** | REST + plugin bridge for community file discovery |
| **Write path** | Can mutate Figma files — out of scope for discovery v1 |

**Fit:** Best for community search, design-system kit extraction, variable/token export when user has Figma Desktop + plugin.

**Risks:** Requires Desktop Bridge for full capability; cloud mode reduces tool surface.

## 2. Official Figma MCP

**Docs:** [developers.figma.com/docs/figma-mcp-server](https://developers.figma.com/docs/figma-mcp-server/)  
**Endpoint:** `https://mcp.figma.com/mcp`

| Aspect | Notes |
|--------|-------|
| **Auth** | OAuth — user must connect Figma account |
| **Read** | File nodes, variables, Code Connect, screenshots |
| **Write** | `use_figma` for approved catalog clients |
| **Limits** | Rate limits; catalog-approved MCP clients only |

**Fit:** Best for **owned files** and org design libraries the user already has access to. Less suited for broad Community browsing without file keys.

**Risks:** OAuth friction; write tools not needed for inspiration pipeline.

## 3. Community template discovery

| Approach | Feasibility |
|----------|-------------|
| Figma Community web search + file keys | Via Figma Console community tools / REST |
| Curated template lists (internal catalog) | High — we own ranking |
| Agent-provided Figma URLs | Parse `file_key` + `node_id` from URL |
| Keyword + tag search | Planned queries from intent + intelligence hints |

**Strategy:** Our `planning/search_planner.py` generates queries; providers execute. We do **not** delegate search strategy to external MCPs.

## 4. Open-source Figma tooling

| Tool | Use |
|------|-----|
| **figma-api** (REST) | File JSON, images — fallback provider |
| **style-dictionary** | Token transform after extraction |
| **figma-transformer** | Node tree normalization |
| **Figwright** | Future provider candidate for codegen-oriented extraction |
| **figma-export** | Asset + style export patterns |

None replace our orchestration — they are extraction/normalization utilities behind providers.

## 5. Design system extraction

| Asset | Source | Normalized to |
|-------|--------|---------------|
| Color / spacing / typography variables | Figma variables API, Console DTCG export | `FigmaExtractionResult.tokens` |
| Components | Component sets + variants | `components[]` + Component DNA |
| Styles | Legacy paint/text styles | tokens (deprecated path) |
| Screenshots | Export API / MCP screenshot tools | Design Snapshot visual section |

Post-extraction: `adapters/ecosystem.to_design_snapshot_payload()` → Design Snapshot Engine.

## 6. Reuse paths in our ecosystem

```text
Extraction
  → design_snapshot_engine (normalize)
  → design_reference_registry (store reference snapshots)
  → consistency_intelligence/discovery (PDG ingest via sources/figma.py)
  → component_intelligence (component DNA matching)
  → design_sense_intelligence (quality critique on snapshot)
```

## 7. Provider selection heuristics (initial)

| Intent | Preferred provider order |
|--------|-------------------------|
| `inspire` | figma_console → official_figma |
| `extract_design_system` | official_figma → figma_console |
| `compare` | official_figma (owned files) |
| `reuse_component` | figma_console → official_figma |
| `learn_patterns` | figma_console → ingest to PDG |

## 8. Non-goals (v1)

- Shipping Figma Console as our MCP
- Autonomous Figma file editing
- Replacing Design Workflow Intelligence Figma hooks
- LLM inside provider layer

## 9. Open questions

1. Community search rate limits and caching strategy
2. License / attribution metadata for Community templates
3. When to prefer REST vs MCP for batch extraction
4. Contract version for multi-intelligence evaluation scores

## References

- [Figma REST API](https://www.figma.com/developers/api)
- [Figma Variables](https://help.figma.com/hc/en-us/articles/15339657135383)
- [DTCG Design Tokens Format](https://design-tokens.github.io/community-group/format/)
- Existing repo: `consistency_intelligence/discovery/sources/figma.py` (PDG ingest only)
