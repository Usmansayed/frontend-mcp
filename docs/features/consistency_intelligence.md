# Consistency Intelligence

**Status:** ✅ shipped (MCP + Project Design Graph)  
**Module:** `src/navigation/consistency_intelligence/`

## Purpose

Consistency Intelligence is the **8th intelligence module**. It ensures the frontend remains **mathematically and visually consistent** with the project's design system (Project Design Graph).

It is **not** responsible for teaching the agent how to design a UI. That belongs to **Design Sense Intelligence** (qualitative UX reasoning, heuristics, layout guidance).

| Module | Question it answers |
|--------|---------------------|
| **Design Sense Intelligence** | "Is this good UX? What should the agent consider?" |
| **Consistency Intelligence** | "Does this match the design system? What is inconsistent and how severe?" |

## Shipped MCP tools

| Tool | Purpose |
|------|---------|
| `perception_design_graph_refresh` | Ingest codebase/tokens/snapshot into Project Design Graph |
| `perception_design_graph_summary` | Graph summary for a `project_id` |
| `perception_consistency_review` | Refresh graph from snapshot + batch audit |
| `perception_consistency_audit` | Batch audit snapshot elements vs graph |
| `perception_consistency_assess` | Assess one selector + actual styles |
| `perception_consistency_propose_fix` | Recommend fix for a `standard_id` |
| `perception_design_knowledge_query` | PDG queries **or** `ux.retrieve` (UX KB) |

## Visual presentation (required for review/audit)

`perception_consistency_review` and `perception_consistency_audit` attach **viewport + full page + section** screenshots by default (`screenshot_pack: auto` → `design`).

After looking at the images, pass **`visual_feedback`** so the tool returns ranked **`next_actions`** (e.g. `verify_section`, `propose_consistency_fix`, `edit_then_remeasure`).

```json
{
  "session_id": "...",
  "scan_id": "...",
  "visual_feedback": {
    "judgment": "needs_work",
    "notes": "header spacing looks tight",
    "focus_sections": ["header"],
    "issues": [{ "section": "header", "problem": "too dense", "wanted": "more gap" }]
  }
}
```

See [visual.md](./visual.md) for pack ladder and feedback loop details.

## Pipeline

```text
observe / Design Snapshot
    ↓
design_graph_refresh (codebase + tokens + snapshot)
    ↓
consistency_review / consistency_audit  (+ inline screenshots)
    ↓
agent LOOKS → visual_feedback → next_actions
    ↓
propose_fix / edit / remeasure
```

## Dependencies on other modules

| Module | Role |
|--------|------|
| Visual & Browser Intelligence | DOM snapshots, computed styles, screenshots |
| Design Snapshot Engine | Measured layout/tokens for audit |
| Codebase / tokens Discovery | Populate Project Design Graph |
| Design Sense Intelligence | Qualitative UX — separate from PDG standards |

## Explicit non-goals

- UX coaching or aesthetic opinions → **Design Sense Intelligence**
- Lighthouse a11y/SEO scores → **Frontend Quality Intelligence**
- Functional correctness → **Visual & Browser Intelligence** (`perception_verify`)
- Treating UX KB principles as Project Design Graph standards

## Related

- [visual.md](./visual.md) — screenshot packs + visual feedback
- [design_sense_intelligence.md](./design_sense_intelligence.md)
- [INTELLIGENCE_MODULES.md](../INTELLIGENCE_MODULES.md)
- [design_decisions.md](../design_decisions.md#adr-015-consistency-intelligence-vs-design-sense)
- Tests: `tests/test_design_visual_evidence.py`, `tests/test_design_evidence_policy.py`
