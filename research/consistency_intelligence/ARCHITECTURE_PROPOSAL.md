# Consistency Intelligence — Architecture Proposal

**Phase:** Complete (Phases 0–5 core)  
**Date:** 2026-07-11 (locked)  
**Status:** Shipped

**Companion docs:**
- [KNOWLEDGE_API.md](./KNOWLEDGE_API.md) — agent interaction, query catalog
- [DISCOVERY_PIPELINE.md](./DISCOVERY_PIPELINE.md) — knowledge sources → pipeline → graph (locked)

---

## 1. Executive summary

Consistency Intelligence is the **project's design knowledge engine** — not a validator.

It learns how *this project* is designed, stores that understanding in the **Project Design Graph**, and serves it through a **Knowledge API** that every agent and intelligence module queries. Validation, auto-fix, Design Sense, and Component Intelligence are **consumers** of the graph. They never maintain their own parallel understanding of the design language.

The engine explains what it learned, why it believes it, how confident it is, what exceptions exist, what alternatives are valid, and what it recommends. **The agent always decides.**

It is not a reviewer, not an LLM, and not a copy of Design Sense architecture.

The engine combines:

| Source | Contribution |
|--------|--------------|
| **NATURALIZE** | Learn conventions from observation; confidence scoring; exceptions |
| **Style Dictionary + DTCG** | Token graph, aliases, normalized interchange |
| **TokenLens** | Coverage, hardcoded detection, fragmentation |
| **Tokens Studio / DesignSystems.one** | Hierarchy ontology (primitive → semantic → component) |
| **OverlayQA** | Live computed-CSS audit methodology |

**Frozen boundary:** Design Sense v1 stays frozen at 87.2%. Consistency Intelligence is a **fresh module** that replaces the current scaffold in `src/navigation/consistency_intelligence/`.

---

## 2. Comparison of researched systems

| System | Primary question | Input | Learning? | Live DOM? | Agent output |
|--------|------------------|-------|-----------|-----------|--------------|
| **NATURALIZE** | Is this name/format conventional *here*? | Source code | ✅ Statistical | ❌ | Ranked suggestions + confidence |
| **Style Dictionary** | How do I export tokens to platforms? | JSON tokens | ❌ | ❌ | Build artifacts |
| **DTCG** | How do tools exchange tokens? | JSON schema | ❌ | ❌ | Spec compliance |
| **TokenLens** | Do CSS files use declared tokens? | JSON + CSS files | ❌ | ❌ | Coverage report |
| **Tokens Studio** | How do teams manage token hierarchy? | Design tools + Git | ❌ | ❌ | Synced token sets |
| **DesignSystems.one** | How do mature DS organize? | Documentation | ❌ | ❌ | Taxonomy / guides |
| **OverlayQA** | Does live UI match tokens/spec? | Live URL (+ optional Figma) | ❌ | ✅ | Violations + tracker export |
| **Consistency Intelligence (proposed)** | What is this project's design language? Is X consistent with it? | DOM + code + optional tokens | ✅ + declared | ✅ | **KnowledgeResponse**: evidence, standards, confidence, exceptions, alternatives, recommendation |

### Capability matrix

| Capability | NATURALIZE | SD | DTCG | TokenLens | OverlayQA | **Ours** |
|------------|:---:|:---:|:---:|:---:|:---:|:---:|
| Learn from implementation | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Declared token ingest | ❌ | ✅ | ✅ | ✅ | partial | ✅ |
| Per-project (not global rules) | ✅ | ✅ | ✅ | ✅ | partial | ✅ |
| Confidence / probability | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Exception handling | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Component relationships | ❌ | ❌ | ❌ | shallow | shallow | ✅ |
| MCP-native | ❌ | ❌ | ❌ | ❌ | Chrome ext | ✅ |
| Auto-fix suggestions | rename | build | ❌ | ❌ | tracker | ✅ agent-mediated |

---

## 3. Ideas to adopt

| # | Idea | Source | Implementation |
|---|------|--------|----------------|
| A1 | **Learn conventions, don't dictate** | NATURALIZE | Discovery Pipeline merges multi-source evidence per context |
| A2 | **Probabilistic standards with confidence** | NATURALIZE | Each standard has `support_count`, `confidence`, `p_value` |
| A3 | **Threshold-gated reporting** | NATURALIZE `PreCommitVerifier` | Only surface violations above confidence cutoff |
| A4 | **Exceptions are first-class** | NATURALIZE (current value in candidate set) | `ExceptionNode` with rationale + approval |
| A5 | **DTCG as token wire format** | DTCG + SD | Ingest/emit compatible JSON; validate with `@dtcg/schemas` |
| A6 | **Reference resolution graph** | Style Dictionary | Alias chains, circular detection for declared tokens |
| A7 | **Token coverage scoring** | TokenLens + OverlayQA study | Per-category adoption % |
| A8 | **Hardcoded value detection** | TokenLens | Raw hex/px where token expected |
| A9 | **Fragmentation detection** | TokenLens (planned) | Near-duplicate tokens/values |
| A10 | **Off-scale / orphan detection** | OverlayQA | Values not on learned scale |
| A11 | **State completeness** | OverlayQA | Missing hover/focus/disabled per component class |
| A12 | **Foundations → components hierarchy** | Tokens Studio, DesignSystems.one | Project Design Graph layers |
| A13 | **Evidence bundles for agents** | NATURALIZE + our MCP philosophy | Every finding includes supporting instances |
| A14 | **Lint consolidation** | Our benchmark learnings | One finding per element, grouped violations |
| A15 | **Design Snapshot as input** | Existing MCP | Never parse DOM in Consistency — consume snapshot |

---

## 4. Ideas to reject

| # | Idea | Source | Why reject |
|---|------|--------|------------|
| R1 | **N-gram LM on source code** | NATURALIZE | Wrong modality; use style property distributions |
| R2 | **Java AST pipeline** | NATURALIZE | Use DesignSnapshot + CSS analysis |
| R3 | **Build-time code generation** | Style Dictionary | We're validation, not export |
| R4 | **Figma-required workflow** | OverlayQA, Tokens Studio | Must work code+DOM only |
| R5 | **AI visual similarity scoring** | OverlayQA Figma plugin | Subjective; Design Sense / Reference Registry |
| R6 | **Global design rules** | Generic linters | Project A ≠ Project B |
| R7 | **Reviewer / specialist architecture** | Design Sense | Different problem; fresh module |
| R8 | **LLM inside engine** | Various | Agent consumes facts; engine is deterministic |
| R9 | **Binary pass/fail only** | TokenLens | Need confidence + alternatives |
| R10 | **Prescriptive DS taxonomy** | DesignSystems.one gallery | Ontology yes, aesthetics no |
| R11 | **Extend current scaffold** | `service.py` placeholder | Replace entirely |
| R12 | **SaaS / account dependency** | TokenLens, OverlayQA | Local MCP execution |

---

## 5. Proposed architecture (locked)

**The Project Design Graph is the product.** Everything else consumes it via the Knowledge API.

```text
Knowledge Sources                ← pluggable evidence producers
  snapshot · codebase · tokens
  figma · opendesign · context7
  user corrections · git · docs (future)
        │
        ▼
Discovery Pipeline               ← merge fragments, score confidence, resolve conflicts
        │
        ▼
Project Design Graph ⭐          ← single source of truth (Phase 1 ✅)
        │
        ▼
Knowledge API                    ← query interface (Phase 1 ✅)
        │
        ├── Consistency Validator      (Phase 3 — thin consumer)
        ├── Auto Fix Proposer          (Phase 3 — thin consumer)
        ├── Design Sense Intelligence
        ├── Component Intelligence
        └── AI Agents (MCP)
```

See [DISCOVERY_PIPELINE.md](./DISCOVERY_PIPELINE.md) for source contracts and merge rules.

### Agent interaction (every query)

```text
Question → Evidence → Learned Standards → Confidence
        → Exceptions → Alternatives → Recommendation → Agent Decision
```

### Module boundaries (locked)

```text
consistency_intelligence/
├── graph/                 # Phase 1 ✅ — Project Design Graph
├── knowledge/             # Phase 1 ✅ — Knowledge API
├── discovery/             # Phase 2 — sources + pipeline
│   ├── pipeline.py
│   ├── context.py
│   ├── merge.py           # Phase 2
│   └── sources/
│       ├── protocol.py    # KnowledgeSource + KnowledgeFragment
│       ├── snapshot.py
│       ├── codebase.py
│       ├── tokens.py
│       ├── figma.py
│       ├── opendesign.py
│       ├── context7.py
│       └── future.py
├── consumers/             # Phase 3 — validator, fix (query graph only)
└── service.py
```

**No `reviewers/`. No owned rule state outside the graph. No LLM inside the engine.**

---

## 6. Proposed data model

### Core types

```python
@dataclass
class LearnedStandard:
    """A probabilistic convention discovered from the project."""
    id: str
    category: str                    # spacing | color | typography | radius | ...
    context: str                     # "button.primary" | "card" | "global"
    property: str                    # padding | border-radius | color
    expected_values: list[str]       # canonical values (may be multiple valid)
    distribution: dict[str, float]   # value → frequency
    confidence: float                # 0-1
    support_count: int               # instances observed
    evidence: list[EvidenceRef]      # supporting DOM instances
    source: str                      # "learned" | "declared" | "merged"

@dataclass
class ExceptionNode:
    """Intentional deviation from a standard."""
    standard_id: str
    element_pattern: str
    actual_value: str
    rationale: str
    approved_by: str | None
    confidence_override: float

@dataclass
class ConsistencyViolation:
    id: str
    standard_id: str
    severity: str                    # blocking | major | minor | advisory
    element: str                       # selector / component id
    property: str
    expected: str | list[str]
    actual: str
    confidence: float
    evidence: list[EvidenceRef]
    sub_violations: list[str]          # lint consolidation children
    suggested_fix: SuggestedFix | None

@dataclass
class ConsistencyReport:
    passed: bool
    summary: str
    project_id: str
    graph_version: str
    coverage: CoverageScores           # per-category TokenLens-style
    standards: list[LearnedStandard]   # discovered norms (for agent context)
    violations: list[ConsistencyViolation]
    exceptions: list[ExceptionNode]
    alternatives: list[AlternativeInterpretation]  # when ambiguous
    degraded: list[str]
```

### DTCG-compatible token node (in graph)

```python
@dataclass
class TokenNode:
    path: tuple[str, ...]
    dtcg_type: str | None
    value: Any
    resolved_value: Any | None
    source: str                        # file path
    layer: str                       # primitive | semantic | component
    extensions: dict[str, Any]       # perception.confidence, etc.
```

### Agent-facing response shape (MCP)

All tools return `KnowledgeResponse`. Validation is one answer type — not a separate error dialect.

```json
{
  "query": { "query_id": "consistency.explain", "params": { "selector": "button.checkout" } },
  "answer": { "consistent": false, "deviations": [ ... ] },
  "evidence": [ ... ],
  "standards": [ { "id": "std_button_padding", "expected_values": ["16px"], "confidence": 0.94, "support_count": 47 } ],
  "confidence": 0.89,
  "exceptions": [],
  "alternatives": [ { "value": "12px", "confidence": 0.08, "note": "ghost variant on marketing pages" } ],
  "recommendation": {
    "action": "align_to_standard",
    "suggested_values": { "padding": "16px", "border-radius": "8px" },
    "confidence": 0.89,
    "rationale": "47 of 50 button instances use 16px padding"
  },
  "graph_version": "pdg_2026-07-10T17:00:00Z"
}
```

Full envelope spec: [KNOWLEDGE_API.md §4](./KNOWLEDGE_API.md#4-knowledge-response-envelope)

---

## 7. Project Design Graph

The PDG is the **DNA store** — not a flat token list.

```text
ProjectDesignGraph
│
├── meta
│   ├── project_id
│   ├── learned_at
│   ├── snapshot_count
│   └── graph_version
│
├── foundations/                    # Layer 1: scales
│   ├── color/
│   │   ├── primitives: TokenNode[]
│   │   └── semantic: TokenNode[]
│   ├── typography/
│   │   ├── families: StandardNode[]
│   │   ├── scale: StandardNode[]     # learned size clusters
│   │   └── groups: TypographyGroup[] # heading, body, caption
│   ├── spacing/
│   │   └── scale: StandardNode[]     # [4,8,12,16,24,32,...]
│   ├── radius/
│   ├── shadow/
│   └── motion/
│
├── components/                     # Layer 2: component DNA
│   ├── button/
│   │   ├── variants: [primary, secondary, ghost]
│   │   ├── states: [default, hover, focus, disabled]
│   │   ├── properties: { padding, radius, color, ... }
│   │   └── relationships: [uses spacing.4, color.primary]
│   ├── input/
│   └── ...
│
├── patterns/                       # Layer 3: composite patterns
│   ├── navbar.floating
│   ├── form.validation
│   └── checkout.shipping
│
├── relationships/                  # Edges
│   ├── component → token
│   ├── component → component (contains)
│   ├── pattern → component
│   └── variant → variant (extends)
│
├── exceptions/                     # Approved deviations
│   └── ExceptionNode[]
│
└── confidence/                     # Graph-level metadata
    ├── per_standard: dict[str, float]
    └── overall_learning_confidence: float
```

### Graph operations

| Operation | Consumer |
|-----------|----------|
| `query_standard(context, property)` | Validator |
| `query_component(name, variant)` | Component Intelligence |
| `query_token_usage(token_path)` | Coverage analyzer |
| `query_pattern(name)` | Design Sense (secondary) |
| `diff_graph(before, after)` | CI / regression |
| `export_dtcg()` | Interop with SD / Tokens Studio |

### Example: two valid projects

**Project A** (floating navbar, 20px padding, 16px radius):
```text
pattern/navbar.floating → confidence 0.91
standard/button.padding → ["20px"] confidence 0.88
standard/button.radius → ["16px"] confidence 0.85
```

**Project B** (fixed navbar, 12px padding, square):
```text
pattern/navbar.fixed → confidence 0.93
standard/button.padding → ["12px"] confidence 0.90
standard/button.radius → ["0px"] confidence 0.87
```

Both pass consistency audits internally. Neither is "wrong."

---

## 8. Phased implementation roadmap

### Phase 0 — Knowledge architecture ✅
- [x] Agent interaction model · [KNOWLEDGE_API.md](./KNOWLEDGE_API.md)

### Phase 1 — Project Design Graph + Knowledge API ✅
- [x] `graph/` — PDG schema + persistence
- [x] `knowledge/` — envelope, API, 21 query stubs
- [x] MCP: `perception_design_knowledge_query`, `perception_design_graph_summary`

### Phase 2 — Ingest knowledge (Discovery Pipeline) ✅
- [x] Implement `collect()` on snapshot, codebase, tokens sources
- [x] Implement `merge.py` — fragment → graph
- [x] MCP: `perception_design_graph_refresh`
- [x] Queries return live data from populated graph

### Phase 3 — Consistency consumers (thin) ✅
- [x] `consumers/validator.py` — composes `consistency.assess` + `consistency.explain` only
- [x] `consumers/fix_proposer.py` — composes `fix.recommend` only
- [x] `consumers/auditor.py` — batch snapshot audit with grouped findings
- [x] Lint consolidation inside assess response (`grouped_deviations`)
- [x] MCP: `perception_consistency_assess`, `perception_consistency_audit`, `perception_consistency_review`
- [x] **No standalone rule engine**

### Phase 4 — Cross-module integration ✅
- [x] Design Sense → `project_design_knowledge` via `integrations/design_sense.py`
- [x] Component Intelligence → `component_guidance.py` queries PDG (`component.*`, `tokens.*`, `spacing.system`)
- [ ] Design Snapshot v2 benchmark gates discovery quality (parallel track)

### Phase 5 — Extended knowledge sources ✅
- [x] Figma, Open Design, Context7 collectors (via `DiscoveryContext.options`)
- [x] User corrections source (`user_corrections.py`)
- [x] Coverage queries: `tokens.used`, `tokens.unused`, `tokens.fragmentation`
- [x] `graph.diff` with version history

### Parallel: Design Snapshot benchmark
- [x] `benchmark/snapshot_gate.py` — extraction vs knowledge readiness

---

## 9. MCP tools (planned)

### Graph-centric (primary)

| Tool | Phase | Purpose |
|------|-------|---------|
| `perception_design_knowledge_query` | 1 | Generic Knowledge API — any `query_id` |
| `perception_design_graph_summary` | 1 | Bootstrap agent with project DNA overview |
| `perception_design_graph_refresh` | 2 | Run Discovery Pipeline → update graph |

### Thin consumers (derived)

| Tool | Phase | Rule |
|------|-------|------|
| `perception_consistency_assess` | 3 | Composes `consistency.*` queries only |
| `perception_consistency_audit` | 3 | Batch assess over snapshot — no owned rules |
| `perception_consistency_propose_fix` | 3 | Composes `fix.recommend` only |
| `perception_design_graph_diff` | 2+ | `graph.diff` query |

---

## 10. Relationship to existing modules

```text
                    ┌─────────────────────────────┐
                    │   Project Design Graph ⭐    │
                    │   (Consistency Intelligence │
                    │    maintains & serves)      │
                    └──────────────┬──────────────┘
                                   │
                          Knowledge API
                                   │
     ┌─────────────┬───────────────┼───────────────┬─────────────┐
     ▼             ▼               ▼               ▼             ▼
 Validator    Fix Proposer    Design Sense    Component Intel.   Agents
 (consumer)   (consumer)      (consumer)      (consumer)      (consumer)
```

| Module | Relationship |
|--------|--------------|
| **Consistency Intelligence** | Owns graph + Knowledge API. Does not own validation logic. |
| **Design Sense** | Queries graph for standards; never re-learns conventions |
| **Component Intelligence** | Queries `component.*` for variants and similarity |
| **Browser Intelligence** | Feeds Design Snapshot into Discovery |
| **Design Snapshot Engine** | Shared substrate — v2 improves discovery quality |
| **Reference Registry** | External product comparison; PDG owns *internal* language |

---

## 11. Success criteria

| Metric | Target |
|--------|--------|
| Clean project (sandbox) | 0 false violations |
| Lint-heavy fixture | 1 consolidated finding per element |
| Declared + observed | Coverage scores match TokenLens within ±5% |
| Learned standards | ≥90% precision on synthetic "known convention" fixtures |
| Agent usefulness | Every violation has evidence + suggested fix |
| Design Sense lift | Generic token findings → 0 (already achieved) |

---

## 12. Research artifacts

| Resource | Document |
|----------|----------|
| NATURALIZE | [resources/01_naturalize.md](./resources/01_naturalize.md) |
| Style Dictionary | [resources/02_style_dictionary.md](./resources/02_style_dictionary.md) |
| DTCG | [resources/03_dtcg.md](./resources/03_dtcg.md) |
| TokenLens | [resources/04_tokenlens.md](./resources/04_tokenlens.md) |
| Tokens Studio | [resources/05_tokens_studio.md](./resources/05_tokens_studio.md) |
| DesignSystems.one | [resources/06_designsystems_one.md](./resources/06_designsystems_one.md) |
| OverlayQA | [resources/07_overlayqa.md](./resources/07_overlayqa.md) |

**Cloned repos:** `research/consistency_intelligence/repos/`

---

## 13. Sign-off checklist

Before Phase 1 implementation:

- [ ] Knowledge-first architecture approved (graph = product)
- [ ] [KNOWLEDGE_API.md](./KNOWLEDGE_API.md) approved (agent interaction + query catalog)
- [ ] PDG ontology approved (§7)
- [ ] `KnowledgeResponse` envelope approved
- [ ] Validator-as-thin-consumer confirmed
- [x] Knowledge Sources → Discovery Pipeline → PDG naming confirmed
- [ ] Design Snapshot v2 requirements fed back to snapshot team

**Phase 0 is documentation-only. No implementation code until sign-off.**
