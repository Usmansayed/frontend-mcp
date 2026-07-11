# Consistency Intelligence — Knowledge API & Agent Interaction

**Phase 0 deliverable** — design before implementation  
**Date:** 2026-07-10  
**Status:** Architecture refinement · no code yet

---

## 1. Core repositioning

Consistency Intelligence is **not** a validator.

It is the **project's design knowledge engine** — the accumulated, queryable understanding of how *this* frontend is designed.

| Old mindset | New mindset |
|-------------|-------------|
| Validator → Rules → Errors | Snapshot → Discovery → **Graph** → **Knowledge API** → Consumers |
| "Radius must be 12px" | "We learned radius 12px on buttons (confidence 0.91, 47 instances); exception on `.legacy-btn`; recommend 12px" |
| Engine decides | Engine **informs**; agent decides |
| Validator owns truth | **Project Design Graph** owns truth |

**The Project Design Graph is the product.** Everything else is a consumer.

---

## 2. System architecture (refined)

```text
Browser Intelligence
        │
        ▼
Design Snapshot
        │
        ▼
Design Snapshot
        │
        ▼
Discovery Pipeline               ← merge knowledge fragments
        │
        ▼
Project Design Graph ⭐          ← single source of truth
        │
        ▼
Knowledge API                    ← query interface for all consumers
        │
        ├── Consistency Validator     (thin — queries graph, never owns state)
        ├── Auto Fix Proposer         (thin — queries graph)
        ├── Design Sense Intelligence
        ├── Component Intelligence
        ├── Future intelligence modules
        └── AI Agents (MCP)
```

### Ingestion path (parallel, feeds Discovery)

```text
Codebase Intelligence ──┐
Declared tokens (DTCG) ─┼──► Knowledge Sources ──► Discovery Pipeline ──► Project Design Graph
Design Snapshot ────────┘
```

Discovery **merges** declared tokens (when present) with observed patterns into one graph. The graph records provenance: `learned` | `declared` | `merged`.

---

## 3. Agent interaction model

Every intelligence module in this MCP should expose the same philosophy: **structured intelligence, not hardcoded decisions.**

### Universal response flow

```text
Question (from agent or module)
        │
        ▼
Evidence              ← DOM instances, file refs, snapshot slices
        │
        ▼
Learned Standards     ← graph nodes matching the query
        │
        ▼
Confidence            ← frequency, support count, declared match
        │
        ▼
Possible Exceptions   ← approved deviations in graph
        │
        ▼
Alternatives          ← other valid values seen in project
        │
        ▼
Recommended Solution  ← engine suggestion (non-binding)
        │
        ▼
Agent Decision        ← always final
```

### What the engine never does

- Issue absolute mandates without evidence
- Auto-apply fixes without agent invocation
- Hide uncertainty
- Maintain parallel rule state outside the graph

### What the engine always does

- Cite what it learned and from where
- State confidence explicitly
- Surface exceptions and alternatives
- Recommend — not enforce

---

## 4. Knowledge response envelope

Every Knowledge API response uses a shared envelope so agents and modules parse consistently.

```python
@dataclass
class KnowledgeResponse:
    """Universal wrapper — all Knowledge API queries return this shape."""

    query: KnowledgeQuery              # what was asked
    answer: KnowledgeAnswer            # structured result (type varies)
    evidence: list[EvidenceRef]        # supporting instances
    standards: list[StandardRef]       # graph standards implicated
    confidence: float                  # 0-1 overall for this answer
    exceptions: list[ExceptionRef]     # relevant approved deviations
    alternatives: list[Alternative]    # other valid interpretations
    recommendation: Recommendation | None  # non-binding suggestion
    degraded: list[str]                # partial data / missing inputs
    graph_version: str
    meta: dict[str, Any]
```

### Sub-types

```python
@dataclass
class EvidenceRef:
    kind: str           # dom | snapshot | source_file | scan
    selector: str | None
    property: str | None
    value: str | None
    scan_id: str | None
    file_path: str | None
    line: int | None

@dataclass
class StandardRef:
    id: str
    category: str
    context: str
    property: str
    expected_values: list[str]
    confidence: float
    support_count: int
    provenance: str     # learned | declared | merged

@dataclass
class ExceptionRef:
    standard_id: str
    element_pattern: str
    actual_value: str
    rationale: str

@dataclass
class Alternative:
    value: str
    confidence: float
    context: str
    note: str

@dataclass
class Recommendation:
    action: str         # use_value | align_to_standard | add_exception | investigate
    detail: str
    suggested_values: dict[str, str]
    confidence: float
    rationale: str
```

**Validation** is a `KnowledgeResponse` where `answer` is a `ConsistencyAssessment` — not a separate error format.

---

## 5. Knowledge API — query catalog

If the graph answers these questions, validation is a small derived capability.

### Foundations & scales

| Query ID | Natural language | Graph traversal |
|----------|------------------|-----------------|
| `standard.for_context` | What is the standard padding for cards? | `foundations.spacing` + `components.card` standards |
| `typography.scale` | Which typography scale does this project use? | `foundations.typography.scale` clusters |
| `spacing.system` | Which spacing system has been learned? | `foundations.spacing.scale` |
| `radius.scale` | Which radius scale has been discovered? | `foundations.radius.scale` |
| `color.palette` | What color roles does this project use? | `foundations.color.semantic` |

### Components & variants

| Query ID | Natural language | Graph traversal |
|----------|------------------|-----------------|
| `component.variants` | Show me every button variant | `components.button.variants` |
| `component.canonical` | What is the canonical version of this component? | highest `support_count` variant cluster |
| `component.similar` | Which component is most similar to this one? | graph similarity on property vectors |
| `component.states` | What interaction states exist for X? | `components.*.states` |

### Tokens & usage

| Query ID | Natural language | Graph traversal |
|----------|------------------|-----------------|
| `tokens.declared` | What tokens are declared? | `foundations.*` declared nodes |
| `tokens.used` | What design tokens are actually used? | `relationships` token → usage edges |
| `tokens.unused` | Which declared tokens are unused? | declared − used |
| `tokens.fragmentation` | Are there near-duplicate tokens? | fragmentation analysis on graph |

### Consistency & fixes

| Query ID | Natural language | Graph traversal |
|----------|------------------|-----------------|
| `consistency.explain` | Why is this inconsistent? | compare element properties vs standards + evidence |
| `consistency.assess` | Is this element consistent? | full assessment for selector/context |
| `fix.recommend` | What is the recommended fix? | `Recommendation` from nearest standard |
| `confidence.for` | How confident are we? | standard.confidence + support_count |

### Exceptions & meta

| Query ID | Natural language | Graph traversal |
|----------|------------------|-----------------|
| `exceptions.for` | Which exceptions exist for this standard? | `exceptions` filtered by standard_id |
| `exceptions.list` | What exceptions exist in this project? | all `exceptions` nodes |
| `graph.summary` | What does this project's design language look like? | high-level PDG summary for agent bootstrap |
| `graph.diff` | What changed since last scan? | graph version diff |

---

## 6. Knowledge API surface (MCP tools)

Phase 0 defines contracts. Implementation follows in Phase 1+.

### Primary tools (graph-centric)

| Tool | Purpose | Returns |
|------|---------|---------|
| `perception_design_knowledge_query` | Generic query by `query_id` + params | `KnowledgeResponse` |
| `perception_design_graph_summary` | Bootstrap agent with project DNA overview | `KnowledgeResponse` |
| `perception_design_graph_refresh` | Run Discovery Pipeline → update graph | graph_version + delta |

### Derived tools (thin consumers — Phase 2+)

| Tool | Implementation rule |
|------|---------------------|
| `perception_consistency_assess` | Calls `consistency.explain` + `consistency.assess` internally |
| `perception_consistency_propose_fix` | Calls `fix.recommend` internally |
| `perception_consistency_audit` | Batch `consistency.assess` over snapshot — **no separate rule engine** |

**Rule:** Derived tools MUST NOT duplicate graph logic. They compose Knowledge API queries.

---

## 7. Example: agent asks about button padding

### Request

```json
{
  "query_id": "consistency.explain",
  "params": {
    "selector": "button.checkout",
    "properties": ["padding", "border-radius"]
  },
  "scan_id": "scan_abc123"
}
```

### Response

```json
{
  "query": { "query_id": "consistency.explain", "params": { ... } },
  "answer": {
    "consistent": false,
    "deviations": [
      { "property": "padding", "actual": "13px", "expected": ["16px"] },
      { "property": "border-radius", "actual": "5px", "expected": ["8px"] }
    ]
  },
  "evidence": [
    { "kind": "dom", "selector": "button.checkout", "property": "padding", "value": "13px", "scan_id": "scan_abc123" },
    { "kind": "dom", "selector": "button.primary", "property": "padding", "value": "16px", "scan_id": "scan_abc123" },
    { "kind": "dom", "selector": "button.secondary", "property": "padding", "value": "16px", "scan_id": "scan_abc123" }
  ],
  "standards": [
    {
      "id": "std_button_padding",
      "context": "button",
      "property": "padding",
      "expected_values": ["16px"],
      "confidence": 0.94,
      "support_count": 47,
      "provenance": "learned"
    }
  ],
  "confidence": 0.89,
  "exceptions": [],
  "alternatives": [
    { "value": "12px", "confidence": 0.08, "context": "button.ghost", "note": "Rare variant on marketing pages only" }
  ],
  "recommendation": {
    "action": "align_to_standard",
    "detail": "Align button.checkout to project button padding and radius norms",
    "suggested_values": { "padding": "16px", "border-radius": "8px" },
    "confidence": 0.89,
    "rationale": "47 of 50 button instances use 16px padding; 3 are legacy marketing overrides"
  },
  "degraded": [],
  "graph_version": "pdg_2026-07-10T17:00:00Z"
}
```

The agent reads this and decides: fix now, add exception, or defer.

---

## 8. Consumer contracts

### Consistency Validator (thin)

```text
assess(element):
  1. knowledge.query("consistency.assess", { selector, scan_id })
  2. if not answer.consistent:
       knowledge.query("consistency.explain", ...)
  3. return KnowledgeResponse (no new logic)
```

No rule registry. No duplicated scales. No local token lists.

### Auto Fix Proposer (thin)

```text
propose(violation):
  return knowledge.query("fix.recommend", { standard_id, element })
```

### Design Sense Intelligence

```text
Before subjective critique:
  summary = knowledge.query("graph.summary")
  standards = knowledge.query("standard.for_context", { context: user_task_region })

Uses learned scales — stops guessing token/spacing norms.
Does NOT own consistency logic.
```

### Component Intelligence

```text
Before recommending a component:
  variants = knowledge.query("component.variants", { component: "button" })
  canonical = knowledge.query("component.canonical", { component: "button" })
  similar = knowledge.query("component.similar", { snapshot_slice })

Adapts recommendations to project DNA.
```

### Future modules

Any new intelligence module:
1. Accepts `graph_version` or triggers `graph.refresh`
2. Queries Knowledge API — never mines conventions independently
3. Returns agent-facing structured intelligence using `KnowledgeResponse`

---

## 9. Discovery Pipeline + Knowledge Sources (locked)

Phase 2 does **not** mean "extract from snapshot." It means **ingest knowledge** from pluggable sources through a merge pipeline.

```text
Knowledge Sources → Discovery Pipeline → Project Design Graph
```

See [DISCOVERY_PIPELINE.md](./DISCOVERY_PIPELINE.md) for full specification.

| Source | `source_id` | Phase |
|--------|-------------|-------|
| Design Snapshot | `snapshot` | 2 |
| Codebase | `codebase` | 2 |
| Declared tokens | `tokens` | 2 |
| Figma | `figma` | 3+ |
| Open Design | `opendesign` | 3+ |
| Context7 | `context7` | 3+ |
| User corrections, git, docs | `future` | later |

Each source emits a `KnowledgeFragment` — never writes the graph directly.

```text
consistency_intelligence/
├── graph/                  # Phase 1 ✅
├── knowledge/              # Phase 1 ✅
├── discovery/              # Phase 2
│   ├── pipeline.py
│   ├── context.py
│   ├── merge.py
│   └── sources/
│       ├── protocol.py
│       ├── snapshot.py
│       ├── codebase.py
│       ├── tokens.py
│       ├── figma.py
│       ├── opendesign.py
│       ├── context7.py
│       └── future.py
└── consumers/              # Phase 3
```
└── consumers/              # Phase 3
```

---

## 10. Revised implementation phases

### Phase 0 — Knowledge architecture ✅

### Phase 1 — Project Design Graph + Knowledge API ✅

### Phase 2 — Ingest knowledge (Discovery Pipeline) ← NEXT

- Implement `collect()` on snapshot, codebase, tokens sources
- Implement `merge.py`
- MCP: `perception_design_graph_refresh`

### Phase 3 — Consistency consumers (thin)
- Queries: `standard.*`, `typography.scale`, `component.variants`, `tokens.*`

### Phase 3 — Consistency consumers (thin)

- `consumers/validator.py` — composes `consistency.*` queries
- `consumers/fix_proposer.py` — composes `fix.recommend`
- Lint consolidation in assess response
- MCP: `perception_consistency_assess`, `perception_consistency_audit`

### Phase 4 — Cross-module integration

- Design Sense reads `graph.summary`
- Component Intelligence reads `component.*`
- Design Snapshot benchmark gates discovery quality

### Phase 5 — Declared token providers

- DTCG ingest enriches graph `declared` layer
- Coverage queries (`tokens.used`, `tokens.unused`)

---

## 11. Long-term vision

```text
Project Design Graph
  = accumulated knowledge of the project's design language
  = grows with every scan, every declared token file, every approved exception
  = shared by every intelligence module and every agent
```

| Consumer | Uses graph for |
|----------|----------------|
| Validation | `consistency.*` queries |
| Auto-fix | `fix.recommend` |
| Component adaptation | `component.*` |
| Design generation | `graph.summary` + standards |
| Future agents | full Knowledge API |
| CI / regression | `graph.diff` |

Consistency Intelligence **maintains and serves** the graph.  
It does not **become** any single consumer.

---

## 12. Sign-off

Phase 0 is complete when this document and the updated architecture proposal are approved.

Implementation of `graph/` and `discovery/` begins in Phase 1 — not before.
