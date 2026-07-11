# SEO Intelligence — Folder Structure

```text
seo_intelligence/
├── __init__.py
├── README.md
├── models.py                 # SeoAuditRequest, SeoEvidenceRef, SeoRecommendation, …
├── service.py                # SeoIntelligenceService facade
├── contract.py               # SeoIntelligenceAdapter for cross-module use
├── registry.py               # SeoProviderRegistry (seed catalog)
│
├── planning/
│   ├── planner.py            # Provider routing
│   └── orchestrator.py       # Full pipeline
│
├── providers/
│   ├── protocol.py           # SeoDataProvider
│   ├── manager.py            # Live adapter registry
│   ├── search_console/
│   ├── analytics/
│   ├── bing/
│   ├── librecrawl/
│   ├── lighthouse/
│   ├── browser/              # Adapter to visual_browser_intelligence
│   └── openseo/              # Optional — MCP to self-hosted OpenSEO
│
├── knowledge/
│   └── graph/
│       ├── seed.py           # Provider metadata nodes
│       └── store.py          # SeoKnowledgeGraphStore
│
├── analysis/
│   └── cross_analyzer.py
│
├── recommendations/
│   └── engine.py
│
├── verification/
│   └── loop.py
│
└── docs/
    ├── ARCHITECTURE.md
    ├── ROADMAP.md
    ├── PROVIDER_MATRIX.md
    ├── KNOWLEDGE_GRAPH_SCHEMA.md
    ├── AUTHENTICATION.md
    ├── SEO_AGENT_GUIDE.md
    └── FOLDER_STRUCTURE.md
```

Tests: `tests/test_seo_intelligence.py`

Research: `research/seo_intelligence/`
