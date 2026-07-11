# Discovery Pipeline — Architecture (Locked)

**Status:** Phase 2 implemented · snapshot, codebase, tokens collectors + merge  
**Date:** 2026-07-10

Phase 1 built the **Project Design Graph** and **Knowledge API**. Phase 2 does **not** mean "extract from snapshot." It means **ingest knowledge** from many sources, merge through a pipeline, and grow the graph.

---

## Core model

```text
Knowledge Sources          ← many evidence producers (pluggable)
        │
        ▼
Discovery Pipeline         ← merge, dedupe, score confidence, resolve conflicts
        │
        ▼
Project Design Graph ⭐    ← single source of truth (already built in Phase 1)
        │
        ▼
Knowledge API              ← query interface (already built in Phase 1)
```

**The PDG is never populated directly by a single module.** Sources emit fragments; the pipeline merges them into the graph.

---

## Knowledge Sources (Phase 2+)

| Source | Package | Input | Phase |
|--------|---------|-------|-------|
| **snapshot** | `discovery/sources/snapshot.py` | `DesignSnapshot` from Browser Intelligence | 2 |
| **codebase** | `discovery/sources/codebase.py` | React/Vue/Svelte files, component AST hints | 2 |
| **tokens** | `discovery/sources/tokens.py` | DTCG JSON, CSS `:root`, Tailwind theme | 2 |
| **figma** | `discovery/sources/figma.py` | Figma tokens/frames via Design Workflow | 3+ |
| **opendesign** | `discovery/sources/opendesign.py` | UX Magic / Open Design projects | 3+ |
| **context7** | `discovery/sources/context7.py` | Framework docs for convention hints | 3+ |
| **user_corrections** | `discovery/sources/future.py` | Agent-approved exceptions, manual overrides | 3+ |
| **git_history** | `discovery/sources/future.py` | Convention drift over time | future |
| **design_docs** | `discovery/sources/future.py` | README, Storybook, DS documentation | future |

Each source implements `KnowledgeSource`:

```python
class KnowledgeSource(Protocol):
    source_id: str

    async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
        """Extract design-language evidence — does NOT write to graph directly."""
```

---

## KnowledgeFragment

Intermediate unit emitted by a source before pipeline merge:

```python
@dataclass
class KnowledgeFragment:
    source_id: str
    standards: list[StandardNode]
    tokens: list[TokenNode]
    components: dict[str, ComponentNode]
    patterns: dict[str, PatternNode]
    relationships: list[RelationshipEdge]
    exceptions: list[ExceptionNode]
    evidence: list[EvidenceRef]
    confidence: float
    degraded: list[str]
```

Multiple fragments from different sources merge in the pipeline. Conflicts resolve by:
1. Higher `support_count` / confidence wins
2. `declared` tokens anchor `learned` observations
3. `user_corrections` / `exceptions` override without deleting standards

---

## Discovery Pipeline

```python
class DiscoveryPipeline:
    def __init__(self, sources: list[KnowledgeSource]) -> None: ...

    async def run(self, ctx: DiscoveryContext, graph: ProjectDesignGraph) -> ProjectDesignGraph:
        fragments = [await s.collect(ctx) for s in self._sources]
        return self._merge(graph, fragments)
```

Pipeline responsibilities (Phase 2):
- Run enabled sources in parallel where safe
- Merge fragments into existing graph (incremental, not replace)
- Bump `graph_version`, update `learned_at`, increment `snapshot_count`
- Record provenance on every node (`learned` | `declared` | `merged` | `user`)

**Not** pipeline responsibilities:
- Answering agent queries (Knowledge API)
- Validation (Phase 3 consumers)
- Auto-fix (Phase 3 consumers)

---

## MCP (Phase 2)

| Tool | Behavior |
|------|----------|
| `perception_design_graph_refresh` | Run Discovery Pipeline with configured sources → save graph → return delta stats |

---

## Module layout (locked)

```text
consistency_intelligence/
├── graph/                 # Phase 1 ✅
├── knowledge/             # Phase 1 ✅
├── discovery/             # Phase 2
│   ├── pipeline.py
│   ├── context.py         # DiscoveryContext
│   ├── merge.py           # fragment → graph merge logic
│   └── sources/
│       ├── protocol.py
│       ├── snapshot.py
│       ├── codebase.py
│       ├── tokens.py
│       ├── figma.py
│       ├── opendesign.py
│       ├── context7.py
│       └── future.py
├── consumers/             # Phase 3 (thin validators/fix)
└── service.py
```

---

## Architecture lock

No further structural changes after this document. Phase 2 implementation adds source collectors and merge logic only.
