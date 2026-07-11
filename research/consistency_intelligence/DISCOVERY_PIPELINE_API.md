# Discovery Pipeline API — Frozen

**Status:** FROZEN as of Phase 2 completion  
**Date:** 2026-07-10

No breaking changes to this API without a version bump (`pdg_api_v2`). Phase 3+ consumers MUST use this surface only.

---

## Entry points

| API | Location | Contract |
|-----|----------|----------|
| `DiscoveryPipeline.run(ctx, graph)` | `discovery/pipeline.py` | Returns `(graph, degraded, MergeStats)` |
| `merge_fragments(graph, fragments)` | `discovery/merge.py` | Incremental merge; never replaces graph |
| `ConsistencyIntelligenceService.refresh_graph(...)` | `service.py` | Runs pipeline + persists |
| MCP `perception_design_graph_refresh` | `design_intelligence_handlers.py` | Same as `refresh_graph` |

---

## `DiscoveryContext` (frozen fields)

```python
@dataclass
class DiscoveryContext:
    project_id: str = 'default'
    repo_root: Path | None = None
    design_snapshot: Any | None = None   # DesignSnapshot
    scan_id: str | None = None
    enabled_sources: frozenset[str] = frozenset({'snapshot', 'codebase', 'tokens'})
    options: dict[str, Any] = field(default_factory=dict)
```

---

## `KnowledgeSource` protocol (frozen)

```python
class KnowledgeSource(Protocol):
    source_id: str
    async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment: ...
```

**Rule:** Sources emit `KnowledgeFragment`. Sources NEVER write `ProjectDesignGraph` directly.

---

## `KnowledgeFragment` (frozen shape)

| Field | Type |
|-------|------|
| `source_id` | `str` |
| `standards` | `list[StandardNode]` |
| `tokens` | `list[TokenNode]` |
| `components` | `dict[str, ComponentNode]` |
| `patterns` | `dict[str, PatternNode]` |
| `relationships` | `list[RelationshipEdge]` |
| `exceptions` | `list[ExceptionNode]` |
| `evidence` | `list[dict]` |
| `confidence` | `float` |
| `degraded` | `list[str]` |

---

## Merge rules (frozen)

1. **Incremental** — existing graph nodes updated, never wholesale replace
2. **Declared > learned** — token conflicts resolve to `declared` provenance
3. **Support wins** — standards merge by `support_count`, then `confidence`
4. **User provenance preserved** — `user` standards keep priority unless higher support overcomes
5. **Meta bumps** — each merge updates `graph_version`, `learned_at`; snapshot source increments `snapshot_count`

---

## Enabled sources (Phase 2)

| `source_id` | Status |
|-------------|--------|
| `snapshot` | Implemented |
| `codebase` | Implemented |
| `tokens` | Implemented |
| `figma` | Stub (Phase 3+) |
| `opendesign` | Stub (Phase 3+) |
| `context7` | Stub (Phase 3+) |
| `future` | Stub |

---

## Sanity gate (passed)

| Check | Result |
|-------|--------|
| Graph grows over multiple refreshes | PASS |
| Declared tokens beat learned | PASS |
| Incremental merge preserves standards | PASS |
| Query latency at 10k components | PASS (`tests/test_consistency_discovery_sanity.py`) |

---

## Phase 3 rule

Validators and fix proposers are **consumers**. They query the Knowledge API only. They do not learn, merge, or store design-language knowledge.
