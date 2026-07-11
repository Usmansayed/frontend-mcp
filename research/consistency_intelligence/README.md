# Consistency Intelligence — Research & Architecture

**Status:** Complete (Phases 0–5 core)  
**Date:** 2026-07-11

Consistency Intelligence is the **project's design knowledge engine**. The **Project Design Graph** is the product; the **Knowledge API** is how agents query it.

## Pipeline

```text
Knowledge Sources
  snapshot · codebase · tokens · figma · opendesign · context7 · user_corrections
        │
        ▼
Discovery Pipeline (frozen API)
        │
        ▼
Project Design Graph ⭐
        │
        ▼
Knowledge API (21 queries)
        │
        └── consumers (validator, auditor, fix proposer, Design Sense, Component Intel)
```

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_design_graph_refresh` | Ingest knowledge into PDG |
| `perception_design_graph_summary` | Bootstrap agent with graph stats |
| `perception_design_knowledge_query` | Generic Knowledge API |
| `perception_consistency_assess` | Single-element assess |
| `perception_consistency_audit` | Batch audit snapshot |
| `perception_consistency_review` | Refresh graph + batch audit |
| `perception_consistency_propose_fix` | Fix recommendation from graph |

## Documents

| Document | Purpose |
|----------|---------|
| [KNOWLEDGE_API.md](./KNOWLEDGE_API.md) | Agent interaction, query catalog |
| [DISCOVERY_PIPELINE_API.md](./DISCOVERY_PIPELINE_API.md) | Frozen pipeline contract |
| [DISCOVERY_PIPELINE.md](./DISCOVERY_PIPELINE.md) | Sources, merge rules |
| [ARCHITECTURE_PROPOSAL.md](./ARCHITECTURE_PROPOSAL.md) | Full synthesis |

## Tests

- `tests/test_consistency_knowledge_phase1.py`
- `tests/test_consistency_discovery_phase2.py`
- `tests/test_consistency_discovery_sanity.py`
- `tests/test_consistency_phase3.py`
- `tests/test_consistency_completion.py`
