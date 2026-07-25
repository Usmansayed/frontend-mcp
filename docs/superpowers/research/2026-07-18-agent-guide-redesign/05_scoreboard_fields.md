# 05 — Scoreboard Fields (what the brain must read)

## Primary readout (prefer one object)

**`agent_summary.episode_card` / `data.episode_card` (`episode_card.v1`)** when present:

| Field | Binding? | Meaning |
|-------|----------|---------|
| `host_action` | Soft | Prose instruction for this turn |
| `gate.state` | Hard | blocked / provisional / ready |
| `gate.next_required_capability` | Soft** | Immediate pitch — **not whole plan** |
| `gate.prohibited_actions` | Hard | e.g. claim_complete |
| `implementation_gate.*` | Hard | sections, ship, residue, completion_criteria |
| `portfolio.unpaid` / `.paid` | Soft→**behaviorally hard** | Families still owed |
| `confidence` | Soft | Process completeness readout, **not a gate** |
| `recommended_resource` | Soft | Which methodology URI to read |
| `what_matters` / `what_matters_now` | Soft | High-impact decisions |

\** Soft in MCP (advisory); guides must make unpaid binding.

## Also on engineering_strategy

| Field | Use |
|-------|-----|
| `influence_level` | Size evidence budget |
| `unresolved_decisions` | What must be resolved before broad code |
| `recommended_evidence` | Singular ROI suggestion — tunnel risk |
| `task_scope` | Align with agent class |
| `surface_type` | Ship challenge flavor |
| `episode_backlog.top` | Best single ROI — use only if in owed plan |
| `stop_conditions` / `defer_until_later` | Obey |
| `evidence_plan` | Open items: complete / skip / supersede |

## Verify / ship signals

| Field | Rule |
|-------|------|
| `ok` | Transport only |
| `data.verified` | Sole verify pass |
| `coordination_evidence.advancement_eligible` | Only true advances structural decisions |
| `ship_gate.council_clear` | Required when ship gated |
| `spec_revision_gate` | revision_required → revise |

## Cognitive load problem

Large docs list **all** fields. Agents latch onto the loudest 1–2.

**Guide design prescription:**

```text
ALWAYS READ (card): unpaid + gate + top
THEN: classify → owed ≤3 → one tool
THEN: influence / verified / ladder flags as needed
DEEP: recommended_resource only when blocked or learning a workflow
```

## Anti-pattern language to avoid in guides

- “Always run `next_required_capability` next” (without unpaid check)  
- “Follow recommended_evidence” as the only instruction  
- Equating `host_action` with a complete plan  
