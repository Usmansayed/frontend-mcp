# Design Sense Intelligence

**Status:** Architecture v1 frozen · orchestration scaffold (v2.2)  
**Module:** `src/navigation/design_sense_intelligence/`  
**Freeze policy:** See [ARCHITECTURE_V1.md](../src/navigation/design_sense_intelligence/ARCHITECTURE_V1.md)

## Purpose

Design Sense Intelligence is **not** a UI generator. It reviews, reasons about, compares, critiques, and improves UI/UX like an experienced product designer.

> We are not reinventing design intelligence. We orchestrate the best existing work and extend it where necessary.

## Pipeline (v1 frozen)

```text
ReviewRequest
      │
      ├─ OBJECTIVE ── reviewers + design_lint (WCAG/math future)
      │
      ├─ SUBJECTIVE ─ reviewers + open_design + uicrit + knowledge + microsoft
      │
      ▼
ReasoningEngine → ReviewCoordinator → DesignReviewReport
```

## Architecture

```text
design_sense_intelligence/
├── ARCHITECTURE_V1.md     # Frozen contracts — read before changing structure
├── models.py
├── service.py
├── contract.py
├── providers/             # External adapters (replaceable)
├── knowledge/             # First-class design knowledge ⭐
│   ├── principles/
│   ├── heuristics/        # Nielsen etc. (not browser runtime heuristics/)
│   ├── psychology/
│   ├── design_patterns/
│   ├── evaluation_rules/
│   ├── knowledge_graph/
│   └── pattern_library/   # SaaS, dashboard, landing, ecommerce, mobile, enterprise
├── rules/                 # Design Lint DOM/CSS port (objective)
├── reviewers/             # Specialist critics + coordinator
├── reasoning/             # Narrative synthesis engine ⭐
├── workflows/             # Microsoft + UICrit methodology
├── learning/              # feedback/, examples/, benchmarks/ (future)
└── heuristics/            # Browser runtime (visual_insights) — unchanged
```

## Knowledge vs providers

| Layer | What it is |
|-------|------------|
| **knowledge/** | Our own curated design knowledge (Gemini research lands here) |
| **providers/** | Adapters to external systems and ported methodologies |

## Open Design

Only direct external integration. Set `OD_DAEMON_URL` for live project search.

## Related

- [consistency_intelligence.md](./consistency_intelligence.md)
- [component_intelligence_architecture.md](./component_intelligence_architecture.md)
