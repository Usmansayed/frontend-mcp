# Resource Intelligence — Folder Structure

Mirrors Component Intelligence and Inspiration Intelligence patterns.

```text
src/navigation/resource_intelligence/
├── __init__.py
├── README.md
├── models.py                    # ResourceAssetRef, LicenseProfile, requests/results
├── service.py                   # ResourceIntelligenceService facade
├── registry.py                  # ResourceProviderRegistry
│
├── intent/
│   ├── parser.py                # NL query → categories + constraints
│   └── lexicon.py               # Category keyword maps
│
├── planning/
│   ├── search_planner.py        # Provider routing, budget
│   └── orchestrator.py          # End-to-end search pipeline
│
├── graph/
│   ├── seed.py                  # Provider seed nodes ✅
│   ├── store.py                 # Persist + query graph
│   └── sync.py                  # Provider metadata refresh jobs
│
├── license/
│   ├── resolver.py              # Asset + provider → LicenseProfile
│   ├── policy.py                # Request gates (commercial, attribution)
│   ├── exclusions.py            # undraw, storyset, …
│   ├── attribution.py           # Build attribution strings
│   └── revalidator.py           # License checklist runner
│
├── ranking/
│   └── ranker.py
│
├── search/
│   ├── executor.py              # Parallel provider calls
│   └── merge.py                 # Dedup across providers
│
├── providers/
│   ├── protocol.py              # ResourceProvider ABC
│   ├── manager.py               # Registry + get()
│   ├── normalize.py             # Common asset shape
│   │
│   ├── iconify/
│   │   ├── provider.py
│   │   ├── client.py
│   │   └── LICENSE.md
│   ├── lucide/
│   ├── fontsource/
│   ├── dicebear/
│   ├── open_doodles/
│   ├── pexels/
│   ├── simple_icons/
│   ├── svg_repo/
│   ├── lottiefiles/
│   └── …
│
├── docs/                        # Architecture (this folder)
│   ├── ARCHITECTURE.md
│   ├── PROVIDER_MATRIX.md
│   ├── RESOURCE_GRAPH_SCHEMA.md
│   ├── LICENSE_INTELLIGENCE.md
│   ├── RANKING.md
│   ├── PLANNING.md
│   ├── MCP_TOOLS.md
│   ├── ROADMAP.md
│   └── FOLDER_STRUCTURE.md
│
└── cache.py                     # Module-scoped TTL caches (optional)

tests/
└── test_resource_intelligence.py

docs/features/
└── resource_intelligence.md     # High-level feature doc
```

## Provider adapter interface (planned)

```python
class ResourceProvider(Protocol):
    provider_id: str

    async def search(
        self,
        query: str,
        *,
        category: ResourceCategory,
        max_results: int,
    ) -> tuple[list[ResourceAssetRef], list[str]]: ...

    def provider_meta(self) -> ResourceProviderMeta: ...
```

## MCP integration (planned)

```text
src/navigation/mcp/
├── handlers.py          # handle_resource_search, …
├── tools.py             # perception_resource_* schemas
├── resources.py         # perception://resource-guide
└── instructions.py      # §14 pointer
```
