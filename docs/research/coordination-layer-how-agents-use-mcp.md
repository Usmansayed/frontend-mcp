# Coordination Layer — How It Works (Agent View)

**Date:** 2026-07-28  
**Purpose:** Exact picture of the coordination layer and how an agent uses Frontend MCP — so we can simplify with eyes open.  
**Not a redesign.** This is “what exists today.”

---

## 0. One-sentence truth

> **You (the host LLM) are the brain. MCP returns deterministic facts + an advisory scoreboard. Coordination does not write UI, invent design, or force tools — it tracks what is paid/unpaid and what you may claim as done.**

---

## 1. Where it lives

| Layer | Path | Role |
|-------|------|------|
| **Live code** | `src/navigation/coordination_intelligence/` | Real coordinator: PSM, gate, portfolio, Ship Council |
| **Frozen research artifacts** | `coordination_layer/` | YAML corpus + distillation — design reference; does not drive runtime by itself |
| **Runtime YAML** | `…/artifacts/runtime/*.yaml` | Capability graph, tool bindings, situation policies |
| **Invisible hook** | `integration/bridge.py` | After almost every MCP tool, refresh strategy onto the envelope |
| **Agent contract** | `.cursor/rules/frontend-perception-mcp.mdc` | What the agent *must* honor |

Kill-switch: `COORDINATION_DISABLED=1` turns the bridge off.

---

## 2. Mental model (3 objects)

```text
┌─────────────────────────────────────────────────────────────┐
│  EPISODE  (ep_…)  — one task arc for a session               │
│    intent, surface, sticky design scope, retry counters      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  PSM (Project Situation Model)                               │
│    situation + evidence ledger + artifacts + constraints     │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  SCOREBOARD (on almost every tool response)                  │
│    agent_summary.coordinator                                 │
│    agent_summary.recommended_next                            │
│    implementation_gate / portfolio unpaid / backlog          │
└─────────────────────────────────────────────────────────────┘
```

**Episode** = “this UI job.”  
**PSM** = world model for that episode.  
**Scoreboard** = what you should read before the next action.

---

## 3. How an agent uses the MCP (exact loop)

### 3.1 Bootstrap (every structural UI task)

```text
1. Read  perception://getting-started   (or recommended_resource)
2. Call  perception_health({ url, intent: "<real task>" })
3. Call  perception_session_start({ base_url, intent })
4. Save  session_id
5. Read  agent_summary.coordinator
         agent_summary.recommended_next
         (optional: engineering_strategy / episode_card)
6. Open  the matching situation card (greenfield / redesign / hotfix / forms …)
```

`intent` matters: without it, greenfield vs hotfix classification is weak.

### 3.2 Scoreboard loop (every structural turn)

```text
Classify task:  greenfield | redesign | mockup | feature | hotfix | polish | forms

Build owed ≤ 3:
  unpaid families ∩ what this class card cares about
  (if unpaid empty → still run the class’s minimum path)

Call ONE tool from owed
  (use gate.next / backlog.top ONLY if it is already in owed)

Re-read unpaid before locking hierarchy / foundation / look

Implement → Done ladder → claim
```

**Hard rule from the agent contract:** MCP will *not* transport-block you for unpaid work — **you** must not tunnel past it.

### 3.3 Browser tools

- Always pass `session_id`
- **One browser tool at a time** (no parallel batches on one session)
- Prefer `navigate_and_observe` / `observe` → LOOK at screenshots → act

### 3.4 Typical greenfield spine (intended)

```text
inspiration collect  →  LOOK (VF purpose=inspiration) + look_lock
  →  optional foundation / component
  →  implement
  →  observe draft  →  VF purpose=design (vs inspiration)
  →  verify (data.verified=true)
  →  section checklist if required
  →  Ship Council if required
  →  claim
```

Redesign/mockup: **snapshot first**, not gallery inspiration.

Hotfix: usually verify only — unless sticky design draft already exists on the episode.

---

## 4. What the scoreboard fields mean

### 4.1 `agent_summary.coordinator` (read this first)

Compact card (`coordinator_card.v1`), roughly:

| Field | Meaning |
|-------|---------|
| `host_action` | Prose “do this next” |
| `gate.state` | `blocked` \| `provisional` \| `ready` \| `maintenance` |
| `gate.next_required_capability` | Capability the gate wants next |
| `gate.prohibited_actions` | e.g. `claim_complete`, `broad_visual_implementation` |
| `implementation_gate` | Full gate object (alias) |
| `portfolio.paid` / `portfolio.unpaid` | Intelligence **families** paid this episode |
| `recommended_resource` | Which guide URI to read |
| `right_sizing` / effort tier | How much ceremony this task deserves |

Also:

- `recommended_next` ≈ `host_action` (or “Gather evidence: …”)
- `episode_card` = coordinator + what matters / surface type
- Full detail lives in `data.engineering_strategy` when present

### 4.2 Unpaid vs gate (the confusion to kill)

| Signal | Nature |
|--------|--------|
| **`portfolio.unpaid`** | **Advisory honesty** — “you haven’t paid inspiration / snapshot / VF yet” |
| **`implementation_gate`** | **Claim contract** — may list `claim_complete` as prohibited |
| Tool transport `ok` | Only means the tool ran — **not** success |

So:

- Unpaid empty ≠ done  
- `ok=true` ≠ verified  
- Only **`data.verified=true`** counts for verify  
- You may still *call* tools while unpaid — the system expects **you** not to invent a full layout while inspiration+snapshot are both unpaid

### 4.3 Portfolio families (examples)

`inspiration`, `inspiration_extract`, `snapshot`, `component`, `observe`, `visual_feedback`, `verify`, `sections`, `residue`, `design_review`, …

Paid when evidence is **advancement_eligible** for that capability (quality flags matter — thin packs don’t fully pay).

Outside design scope (pure hotfix/minimal), unpaid lists may be empty with note `N/A outside design scope`.

---

## 5. Done ladder (when you may claim)

Order:

```text
1. Gate allows claim  (claim_complete not prohibited)
2. perception_verify → data.verified = true
3. Section checklist  (if section_checklist_required)
4. Ship Council       (if ship_council_required)  via design_review mode=ship
5. Spec revision      (if Spec bound and revision_required)
6. Then claim “done”
```

**Ship Council** = post-draft design challenges ranked by ROI; not a second invent-UI step.

**Sticky design scope:** if the episode started as design/redesign, later “just polish” turns can still owe sections/ship. Surprising, intentional.

---

## 6. Inspiration inside coordination (today)

| Situation | Coordination behavior |
|-----------|------------------------|
| **Greenfield / design_driven** | Unpaid often includes **`inspiration`** (or snapshot as alternative). After collect without look-lock → unpaid **`inspiration_extract`** (VF purpose=inspiration). |
| **Redesign / mockup** | **Snapshot-first** — inspiration kept off unpaid so agents don’t tunnel into galleries. |
| **Hotfix** | Usually no inspiration unpaid. |

Important:

- Collect alone ≠ direction locked  
- Direction locks when VF inspiration fills **look_lock / borrow / primary_ref_ids**  
- Inspiration Intelligence (the layer we just hardened) is the **provider**; coordination only **tips** when it is owed

We have **not** yet simplified coordination to “always force inspiration for most tasks.” That is the next product decision, after this doc.

---

## 7. Tool map (agent cheat sheet)

| Need | Tools |
|------|--------|
| Start | `perception_health`, `perception_session_start` |
| See page | `perception_navigate_and_observe`, `perception_observe` |
| Creative refs | `perception_inspiration_collect` (+ discover / pulse / widen) |
| Lock look | `perception_visual_feedback` (`purpose=inspiration` then `design`) |
| Measure mockup | `perception_build_design_snapshot` |
| Components | `perception_search_components`, `select_component_foundation`, … |
| Forms | `perception_probe_form`, `probe_guards` |
| Proof | `perception_verify` |
| Ship | `perception_design_review` (`mode=ship`) |
| Optional coord | `perception_coordinator_briefing`, `episode_start`, `apply_envelope` |

Resolvers (`perception_resolve_*`) for code↔route — not `perception_code_context`.

---

## 8. Situation cards (progressive disclosure)

| Task class | Resource |
|------------|----------|
| Every structural turn | `perception://guide/scoreboard` |
| New landing / greenfield | `perception://guide/greenfield` |
| Redesign / mockup | `perception://guide/redesign` |
| Feature | `perception://guide/feature` |
| Hotfix / polish | `perception://guide/hotfix` |
| Forms | `perception://guide/forms` |
| Hard fails | `perception://guide/hard-fails` |
| Effort | `perception://guide/right-sizing` |

Deeper: `perception://design-workflow`, `verification-guide`, `ship-council`, `engineering-strategy`, `agent-coordination`.

---

## 9. Why it feels heavy (simplify candidates)

This is the honest “what’s overbuilt” list — not bugs, **ceremony**:

1. **Too many voices** — `coordinator` + `engineering_strategy` + `episode_card` + `host_action` + `recommended_next` + `backlog.top` + `recommended_evidence`. Agents tunnel on one pitch.
2. **Advisory unpaid vs claim gate** — two systems that look like one.
3. **Done ladder stack** — sections + residue remasure + Ship Council + SpecDiff + right-sizing demotions (`*_advisory`).
4. **Sticky design scope** — hotfix later still owes design ceremony.
5. **Large YAML surface** — clusters, playbooks, heuristics, evidence lattice (needed for determinism; hard to learn).
6. **Invisible bridge** — strategy refreshes on every tool; easy to ignore until claim fails.

**Design stance already in-repo:** better agent behavior beats more coordination code. Simplify should mean **fewer signals, clearer owed ≤3, lighter claim path** — not a second brain inside MCP.

---

## 10. Simplify direction (after you read this)

When we simplify, aim for:

```text
Bootstrap → one card (owed + gate + next tool)
  → gather unpaid evidence (inspiration-first on greenfield)
  → implement
  → verify
  → claim
```

Keep:

- Episode / PSM as internal state  
- `data.verified=true`  
- Inspiration unpaid for greenfield  

Cut or demote:

- Duplicate scoreboard fields  
- Ship / sections for light tiers by default  
- Anything the agent must read that doesn’t change the next tool call  

---

## 11. Code pointers

| Want | Open |
|------|------|
| Bridge (tool → strategy) | `src/navigation/coordination_intelligence/integration/bridge.py` |
| Coordinator card | `…/planning/coordinator_card.py` |
| Unpaid portfolio | `…/planning/episode_portfolio.py` |
| Implementation gate | `…/planning/implementation_readiness.py` |
| Snapshot vs inspiration | `…/planning/reference_routing.py` |
| Ship Council | `…/planning/ship_council.py` |
| Agent short contract | `.cursor/rules/frontend-perception-mcp.mdc` |
| Frozen research root | `coordination_layer/README.md` |

---

## 12. Bottom line

Coordination is a **scoreboard + claim gate**, not a designer.

An agent succeeds when it:

1. Bootstraps with real `intent`  
2. Pays **owed ≤3** evidence before inventing UI  
3. Uses Inspiration for greenfield creative input (LOOK + lock)  
4. Proves with `data.verified=true` and finishes the Done ladder only when required  

That is the exact system. Simplify from here — don’t add another layer until this picture is the shared ground truth.
