---
name: frontend-engineering-with-perception
description: >-
  Frontend engineering methodology with Frontend Perception MCP. Use when building
  or changing web UI (pages, dashboards, landings, forms, CSS, redesign, polish,
  frontend bugs) — especially greenfield product UI or when the agent might
  scaffold pages before design evidence. Teaches phase workflow and reading the
  coordinator scoreboard; not a tool catalog.
---

# Frontend Engineering with Perception

You are the brain. Frontend MCP is a deterministic evidence runtime (facts + advisory scoreboard). It does not replace your judgment.

**Adoption metric that matters:** design evidence exists before the first major UI scaffold — not tool-call count.

## Bootstrap (every applicable UI task)

1. `perception_health({ url, intent })` with the **real user task**
2. `perception_session_start({ base_url, intent })` → save `session_id`
3. Read **`agent_summary.recommended_next`** and **`agent_summary.coordinator`** before planning large code
4. Obey `implementation_gate` while blocked (evidence / scaffold only)
5. Read `recommended_resource` or the matching situation card

Without **intent**, greenfield vs hotfix routing is weak — always pass it.

## Phase branches (not a tool list)

| Class | Before large code | Done when |
|-------|-------------------|-----------|
| Greenfield | Design orientation: inspiration **or** snapshot + foundation as unpaid requires | Verify + Done ladder |
| Redesign / mockup | Snapshot bind first | SpecDiff honest + ladder |
| Feature | Observe affected surface; bound Spec if any | Verify (+ ladder if gated) |
| Hotfix | Observe blocking → smallest fix | `data.verified=true` |
| Forms / flows | probe_form / probe_guards / checkpoints | Criteria pass |

Soft text verify is never redesign-done. `ok` ≠ `data.verified`.

## Coordinator channel

| Field | Use |
|-------|-----|
| `recommended_next` | One-line next action |
| `coordinator` | Gate, unpaid/paid, host_action |
| `episode_card` | Single readout |
| `engineering_strategy` | Full influence / decisions |

Coordinator is **advisory**. Do not tunnel on `gate.next` alone while other structural unpaid remain. Build owed ≤3 from unpaid ∩ class.

## Hard invariants

- No claim-done without Done ladder when checklist/ship required
- Blocking before advisory
- One browser tool at a time per `session_id`
- Never `perception_code_context` — use `perception_resolve_*`

## Progressive disclosure

Short always-on rule + this skill for phases. Deep playbooks live on MCP resources (`perception://getting-started`, `guide/*`, workflow URIs). Do not duplicate a 40-tool catalog here.
