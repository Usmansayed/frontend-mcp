# Design Sense Intelligence

**Status:** Architecture v1 frozen · UX Knowledge Brain provider wired  
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
      ├─ SUBJECTIVE ─ reviewers + open_design + uicrit + microsoft
      │               + design_knowledge (static psychology/principles)
      │               + ux_knowledge (ForOpenCode UX KB — playbooks/psychology)
      │               + crit_rams
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
│   └── ux_knowledge/      # ForOpenCode retrieve adapter (peer to PDG)
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
| **knowledge/** | Curated Design Sense knowledge (psychology laws, Nielsen, pattern library) |
| **providers/ux_knowledge** | Adapter to ForOpenCode UX Knowledge Brain (`ux.retrieve`) — evidence-backed playbooks |
| **providers/** (other) | Open Design, UICrit, Microsoft, Design Lint, Crit/Rams |
| **Consistency / PDG** | Project-local tokens/components — **not** merged with UX KB |

## MCP usage

```json
{
  "user_task": "Reduce cognitive load on dashboard KPI hierarchy",
  "scope": "page",
  "repo_root": "C:/path/to/frontend-perception-engine",
  "scan_id": "<from observe>",
  "screenshot_pack": "auto",
  "visual_feedback": {
    "judgment": "needs_work",
    "notes": "KPI row feels equal-weight",
    "focus_sections": ["main"]
  }
}
```

Tool: `perception_design_review`. Without `repo_root`, UX KB falls back to process CWD (may miss corpus).

By default the tool attaches **viewport + full page + section** screenshots. After looking, pass `visual_feedback` to receive ranked `next_actions`. See [visual.md](./visual.md).

Direct retrieval: `perception_design_knowledge_query` with `query_id: "ux.retrieve"`.

## Open Design

Only direct external integration. Set `OD_DAEMON_URL` for live project search.

## Related

- [consistency_intelligence.md](./consistency_intelligence.md)
- [component_intelligence_architecture.md](./component_intelligence_architecture.md)
- `ForOpenCode/kb/schemas/RETRIEVAL_CONTRACT_v1.md`
