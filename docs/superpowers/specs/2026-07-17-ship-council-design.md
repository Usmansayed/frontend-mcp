# Ship Council

## Goal

Add a post-draft quality gate that changes the conversation from **"Does it pass?"** to **"Should we really ship it like this?"**

Ship Council is a **mode** of the existing design-review surface — not a new top-level MCP tool. It is a short, ranked, **decision-centric** challenge meeting held after UI exists and before the agent claims finished.

## Framing

When Ship Council runs, the agent-facing output begins with:

```text
Ship Council

You're about to ship this frontend.

Here are the N highest-ROI decisions we'd challenge before approving release.
```

Core question for every challenge:

> Would an experienced frontend engineer approve shipping this?

When Ship Council finishes (clear or stop), emit a **Ship Summary**:

```text
Ship Summary

Challenges Raised: 4
Revised: 3
Accepted: 1
Asked User: 0

Estimated UI Improvement: High
Ship Confidence: 92%
```

---

## Integration Principle: No New Top-Level Tool

The MCP surface already includes Engineering Strategy, Design Review, SpecDiff, Verify, and Coordination. Ship Council must **not** add `perception_ship_council`.

### Surface

Ship Council is a **mode of `perception_design_review`**:

```text
perception_design_review(mode="ship")
```

| `mode` | Behavior |
|--------|----------|
| `"review"` (default) | Existing multi-lane Design Review + SpecDiff + revision gate |
| `"ship"` | Ship Council: top 3–5 ROI-ranked challenges, ship gate, ledger dispositions, ship summary |

### Auto-ship

When **all** are true, the coordinator / handler may default or recommend `mode="ship"`:

1. A measurable draft exists (snapshot or observe)
2. `verify` passed (blocking empty)
3. `influence_level` is `structural` or `balanced`
4. Implementation is post-draft (not pre-code / blocked gate)

Hosts that call `perception_design_review` without `mode` after verify on structural/balanced work should receive a coordinator hint to re-run with `mode="ship"` or get ship output inline when auto-ship applies.

`recommended_resource` may point at `perception://ship-council` (methodology only). `recommended_capability` remains `design_review` with ship mode — not a new capability id in the effort allocator.

---

## Role in the Stack

| Piece | Job |
|-------|-----|
| Engineering Strategy + `implementation_gate` | What to resolve **before** broad coding |
| Design Review (`mode=review`) | Multi-lane findings / scores (evidence input) |
| SpecDiff / `spec_revision_gate` | Measurable drift vs bound Spec |
| Verify | Runtime blocking truth — *does it work?* |
| **Ship Council (`mode=ship`)** | Ranked ship challenges — *should we ship it like this?* |
| **Decision Ledger** | Single artifact for decision lifecycle through ship |

Ship mode **consumes** review findings, SpecDiff, strategy, and verify state. It **rewrites** high-impact signals into decision challenges. It must not surface 15 lint-style findings.

---

## Decision Ledger (Unified Lifecycle)

Do not introduce a parallel runtime for challenges, dispositions, and accepted reasons. Extend the **Decision Ledger** (PSM episode + `perception://decision-ledger`).

### Lifecycle

```text
Decision
  ↓
Evidence
  ↓
Challenge        ← Ship mode emits this
  ↓
Disposition      ← revised | accepted | ask_user
  ↓
Verification     ← remeasure / re-verify after revise
  ↓
Closed
```

### Ledger entry (ship phase)

Each challenge is a ledger entry keyed by stable `decision_id` / `signal`:

```json
{
  "decision_id": "nav_sticky_behavior",
  "decision": "Navigation",
  "phase": "challenge",
  "question": "Sidebar scrolls with content. Is this intentional for a productivity dashboard?",
  "why_it_matters": "Persistent navigation reduces context switching.",
  "severity": "major",
  "roi_score": 0.89,
  "expected_roi": "high",
  "default_action": "revise",
  "owner": "agent",
  "evidence_refs": ["design_review:finding_12", "specdiff:layout.nav.position"],
  "disposition": null,
  "accept_reason": null,
  "closed_at": null
}
```

After disposition:

```json
{
  "phase": "closed",
  "disposition": "accepted",
  "accept_reason": "Sidebar is intentionally non-sticky because this dashboard is optimized for short pages and avoids reducing horizontal space on 13-inch laptops.",
  "closed_at": "2026-07-17T12:00:00Z"
}
```

Re-runs suppress ledger entries that are `closed` with `accepted` **unless** the live signal changed (evidence no longer supports the prior challenge). `revised` entries may reopen if the signal persists after remeasure.

`coordination_evidence` for ship-mode design_review records whether the run produced usable challenges and whether the ship gate cleared.

---

## When Ship Mode Runs

After **ACT** has produced measurable UI, after **VERIFY** (`data.verified=true`), after
**section checklist** is complete when required, and before claim-done.

| Influence / mode | Behavior |
|------------------|----------|
| `structural` / `balanced` / `design_driven` / `redesign` | Required before claiming done while any open high-ROI major+ challenge remains undisposed |
| `minimal` / hotfix / surgical / debug | Skip ship mode (`ship_gate.state=skipped`) |
| Polish saturation `hard` | Cap challenges; prefer stop + ship summary over endless critique |

Claim-done for visual drafts requires **all** that apply:

1. `data.verified=true` (blocking empty)
2. Section checklist complete when `section_checklist_required`
3. `ship_gate.council_clear === true` when `ship_council_required`

---

## Dynamic ROI (Evidence-Derived, Not Hardcoded)

ROI scores must **not** be fixed per decision family (e.g. hierarchy always 95%). Each challenge's `roi_score` is computed from live evidence:

```text
roi_score = normalize(
  severity_weight
  × strategy_weight
  × lifecycle_weight
  × specdiff_magnitude
  × visual_improvement_estimate
)
```

### Inputs

| Factor | Source |
|--------|--------|
| `severity_weight` | Finding severity, SpecDiff item severity, revision_gate blocking |
| `strategy_weight` | Engineering strategy: influence level, unresolved decision impact, recommended_evidence priority |
| `lifecycle_weight` | Posture (draft vs verified), polish saturation, verify recency |
| `specdiff_magnitude` | `impact_weight`, drift count, bound-reference delta for the decision family |
| `visual_improvement_estimate` | Snapshot signals (layout class, hierarchy spread, theme token coupling, responsive breakage) |

### Ranking rules

- Rank all candidate challenges by computed `roi_score`
- Emit **top 3–5** only; drop below cut line (e.g. padding nits at 18%)
- `expected_roi` band: `high` ≥ 0.75, `medium` ≥ 0.45, `low` < 0.45 (tunable)
- Same dashboard type does not guarantee same questions — evidence mix changes ranking

### Question templates

Signal **templates** (wording for `question` / `why_it_matters`) are versioned and stable. **ROI is never hardcoded on the template.** Templates map `signal` → copy; scoring is always per session.

Initial decision families:

1. Navigation chrome
2. Layout pattern (marketing-centered vs product shell)
3. Information hierarchy
4. Theme coupling
5. Composition
6. Responsive structure

---

## Ship Mode Output Shape

```json
{
  "mode": "ship",
  "framing": "You're about to ship this frontend. Here are the highest-ROI decisions we'd challenge before approving release.",
  "challenges": [
    {
      "decision_id": "hierarchy_focal_point",
      "decision": "Information Hierarchy",
      "question": "All KPI cards have equal visual weight. Should revenue become the dominant focal point?",
      "why_it_matters": "Equal weight flattens scanning; users miss the primary business signal.",
      "severity": "major",
      "expected_roi": "high",
      "roi_score": 0.91,
      "default_action": "revise",
      "owner": "agent",
      "signal": "equal_weight_kpi_cluster",
      "evidence_refs": ["specdiff:hierarchy.kpi_weights", "design_review:hierarchy_lane"]
    }
  ],
  "ranked_roi": [
    {"decision": "Information Hierarchy", "roi_score": 0.91},
    {"decision": "Dashboard Composition", "roi_score": 0.87},
    {"decision": "Sidebar Behavior", "roi_score": 0.84}
  ],
  "ship_gate": {
    "state": "challenge",
    "open_high_roi": 3,
    "council_clear": false
  },
  "ship_summary": null
}
```

When `ship_gate.council_clear` is true (or stopped by polish saturation):

```json
{
  "ship_summary": {
    "challenges_raised": 4,
    "revised": 3,
    "accepted": 1,
    "asked_user": 0,
    "estimated_ui_improvement": "high",
    "ship_confidence": 0.92
  }
}
```

`ship_confidence` is derived from: share of challenges dispositioned, severity cleared, verify state, spec_revision_gate, and remaining open ledger entries — not a static constant.

---

## Dispositions

Submitted on `perception_design_review` with `mode="ship"` and optional `dispositions` array (or a dedicated follow-up arg on the same tool — no new tool).

| Disposition | Allowed | Requirements |
| ----------- | ------- | ------------ |
| `revised` | Yes | Default. Agent changes UI → remeasure → verify → ship mode again. |
| `accepted` | Yes | Concrete engineering rationale (product, UX, a11y, performance, responsiveness, requirements). No user required. |
| `ask_user` | Yes | Subjective brand, visual identity, product strategy, or conflicting requirements only. |

Hollow accepts fail closed (`"Looks fine."` → undisposed).

### Agent vs user

| `owner` | When | `default_action` |
|---------|------|------------------|
| `agent` | Established product/UI conventions | `revise` |
| `user` | Branding, artistic direction, positioning | `ask_user` |

---

## Ship Gate

```json
{
  "ship_gate": {
    "state": "clear" | "challenge" | "awaiting_user" | "skipped",
    "open_high_roi": 0,
    "council_clear": true
  }
}
```

- `clear` — no open high-ROI major+ challenges (all revised or accepted with valid rationale)
- `challenge` — open agent-owned challenges remain
- `awaiting_user` — `ask_user` challenge open
- `skipped` — influence/mode does not require ship council

`council_clear` is true when state is `clear` or `skipped`. Composable with verify; do not fold verify into this object.

---

## Surfaces (Revised)

1. **`perception_design_review`** — add `mode: "review" | "ship"` and optional `dispositions[]`; ship mode returns challenges, ship_gate, ship_summary, ledger updates
2. **`perception://ship-council`** — methodology resource (when to run, dispositions, claim-done); points at design_review ship mode
3. **`perception://decision-ledger`** — extend to document ship lifecycle phases (Challenge → Disposition → Closed)
4. **Coordinator / `agent_summary`** — `ship_gate`, `section_checklist`, `recommended_capability`, hint `mode: ship` when post-verify structural/balanced
5. **Cursor rule** — Done ladder: `data.verified` → section checklist → Ship Council; never claim done while gates prohibit `claim_complete`
6. **`perception://verification-guide`** — verify ≠ claim-done; section checklist + ship mode when required

---

## Loop

```text
ACT (draft UI)
  → OBSERVE / Design Snapshot (seeds section_checklist)
  → VERIFY (data.verified=true)
  → Section checklist: observe → look → verify(section_id) per block
  → perception_design_review(mode="ship")
  → for each ledger challenge:
        revise → remeasure → verify → ship mode again
        OR accept + engineering rationale → ledger closed
        OR ask_user (subjective only)
  → ship_gate.council_clear + ship_summary
  → claim done
  OR polish saturation / stop_conditions → ship_summary + stop
```

---

## Non-Goals (v1)

- No new top-level MCP tool
- No LLM inside MCP for challenge prose (templates + evidence-derived ROI)
- Not a replacement for review-mode scores or SpecDiff property diffs
- Not a pre-code gate (`implementation_gate` remains separate)
- Not unlimited critique loops (ROI cut + polish saturation)
- Not user interruption for convention gaps

---

## Success Criteria

- Agents treat post-draft work as a ship meeting, not a green verify checkbox
- MCP surface stays small: one tool, two modes
- ROI varies by session evidence, not fixed hierarchy/sidebar percentages
- Challenges, dispositions, and accepts live in Decision Ledger — one engineering artifact
- Ship Summary gives agent and user a concise pre-ship record
- Structural/balanced done requires verify + `ship_gate.council_clear`

---

## Revision History

- **2026-07-17 (initial):** Ship Council as standalone tool concept
- **2026-07-17 (rev 2):** Integrate into `perception_design_review(mode="ship")`; evidence-derived ROI; Decision Ledger lifecycle; Ship Summary
