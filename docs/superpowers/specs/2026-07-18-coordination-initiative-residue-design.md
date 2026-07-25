# Coordination Initiative & Residue Layer

**Date:** 2026-07-18  
**Status:** Approved for implementation (2026-07-18)  
**Scope (v1):** `design_driven` / `redesign` / `system_setup` episodes, and `influence_level` in `{structural, balanced}` when sticky design scope applies. Hotfix / surgical / debug / pure maintenance stay on the surgical path.

## Problem

Frontend MCP can move some decisions (chrome sticky, theme, foundation) and still ship UIs that look unfinished. Root causes:

1. **Tunnel vision** — `recommended_evidence` and `host_action` highlight one next step; `evidence_plan` is never checked against the capability ledger.
2. **One-size heuristics** — dashboard, settings forms, auth, and marketing share the same Ship / layout signals.
3. **Thin ship clear** — Ship Council can clear with weak snapshot coverage while residue (uneven KPIs, form measure, footer collision) remains.
4. **Consistency-as-excuse** — agents copy dashboard full-bleed onto settings because nothing asks for surface-appropriate measure.

The coordinator currently thinks **one step ahead** instead of managing the **whole engineering episode**.

## Goals

| Goal | Success signal |
|------|----------------|
| Episode backlog | Strategy always exposes ranked open work; top item = highest Engineering ROI next action |
| Surface type | First-class discriminator; different ship/layout judgments by surface |
| Evidence completion (anti-tunnel, not busywork) | Claim-complete blocked only when plan items are neither completed, validly skipped, nor superseded |
| Residue scan | At most **one** extra remeasure/challenge pass before ship may clear |
| Initiative | Advisory portfolio of unpaid intelligence families — **not** a new gate |
| Episode confidence | Single % + contributors so agent/user see process completeness at a glance |

## Non-goals (v1)

- New MCP tools or a second runtime
- Forcing every recommended intelligence family to run
- Endless polish recursion after residue
- Changing hotfix / surgical Done ladder
- Hard-blocking tool calls at the transport layer (still advisory `prohibited_actions` + louder host_action; same enforcement model as today)

## Design principles

1. **Extend existing surfaces** — `implementation_gate`, `engineering_strategy`, Ship Council, decision ledger, PSM `retry_counters` / evidence ledger.
2. **ROI over completeness** — backlog priority answers: *What is the single highest-impact thing to do next?*
3. **Completion without ritual** — evidence-plan items may be completed, **skipped with reason**, or **superseded by stronger evidence**.
4. **Surface-aware judgment** — same pixel patterns mean different things on dashboard vs settings vs auth vs marketing.
5. **Bounded residue** — one pass max; then dispose or accept with rationale.

---

## 1. Surface type (first-class discriminator)

### Field

`surface_type` on strategy discriminators and PSM episode metadata:

| Value | Typical intent / layout cues |
|-------|------------------------------|
| `dashboard` | KPI rows, charts, data tables, hybrid chrome |
| `settings_form` | Preference groups, toggles, Save/Reset footer |
| `auth` | Login / signup / forgot-password |
| `marketing` | Landing / promo / centered hero |
| `data_table` | CRM-style dense tables (optional v1 alias under dashboard if sparse) |
| `mixed` | Multiple primary surfaces in one episode |
| `unknown` | Insufficient signal — conservative defaults |

### Derivation (deterministic)

1. Intent keywords (settings, preferences, login, landing, dashboard, customers table, …).
2. Snapshot layout cues when available (form density, KPI grid, hero centering, table dominance).
3. Sticky for the episode once set to a non-`unknown` value unless a stronger multi-route observe proves `mixed`.

**Storage (episode context — not retry state):**

```text
episode
├── surface_type          # first-class EpisodeState field
├── intent / influence…   # existing
├── backlog               # compiled onto strategy each refresh (not necessarily persisted raw)
└── retry_counters        # verify loops, capability_attempts, residue_scan flags, evidence_plan_status
```

Do **not** store `surface_type` inside `retry_counters`.

### Effects by surface

| Surface | Prefer challenges | Soften / skip |
|---------|-------------------|---------------|
| `dashboard` | KPI hierarchy (type-only fixes), uneven columns, composition, chrome conventions | Marketing-centered main as default “fix” |
| `settings_form` | **Form measure** (~0.70–0.85 content width), **footer breathing room**, theme coupling | `equal_weight_kpi_cluster`; don’t demand dashboard KPI layout |
| `auth` | Split vs card composition, contrast, chrome minimal | Dashboard KPI / dense composition |
| `marketing` | Hierarchy, hero budget, narrow/centered shell when intentional | Forcing full product shell |
| `mixed` | Per-route backlog items with surface tags | Single global heuristic |

New ship signals (v1):

- `settings_form_measure` — main/settings content width_ratio ≳ 0.90 beside a product shell when surface is settings_form (challenge: tighten measure / center content column).
- `settings_footer_collision` — primary actions within ~24–40px of last section edge / viewport bottom with insufficient padding (challenge: add footer rhythm).

Accept remains valid when the agent supplies engineering rationale (e.g. “settings share dashboard content column by design system”).

---

## 2. Episode backlog (ROI-ranked)

### Shape

```json
{
  "episode_backlog": {
    "top": {
      "id": "…",
      "kind": "structural_decision|section|ship_challenge|residue|evidence_gap",
      "title": "…",
      "roi_score": 0.0,
      "why_now": "…",
      "suggested_capability": "…",
      "surface_type": "settings_form"
    },
    "items": [ /* up to 8, sorted by roi_score desc */ ],
    "answered_next": "What is the single highest-impact thing to do next?"
  }
}
```

### Sources (merged, deduped)

1. Unresolved structural / high-priority decisions (`_collect_unresolved`).
2. Incomplete section checklist blocks (when required).
3. Open Ship Council challenges (undisposed).
4. Evidence-plan gaps (incomplete and not skipped/superseded).
5. Residue findings (at most once per episode — see §4).

### ROI ranking

Reuse Ship-style ROI ingredients where possible: severity × influence × surface relevance × whether blocking claim-complete.  
**`top` is always items[0]** — the answer to the single highest-impact next action.

### Surfacing

- `engineering_strategy.episode_backlog`
- `host_action` leads with backlog top when gate allows (else keep gate language first, then backlog top)
- `agent_summary.blocking` may include up to 3 backlog titles when claim is prohibited

---

## 3. Evidence-plan completion (no ritual calls)

### Allowed terminal states per plan item

| State | Meaning |
|-------|---------|
| `completed` | Ledger shows usable evidence for that capability (`advancement_eligible=true` or equivalent succeeded outcome for that decision) |
| `skipped` | Explicit skip recorded with **valid reason** (see below) |
| `superseded` | Stronger evidence closed the same decision (e.g. Figma bind supersedes inspiration; live foundation select supersedes soft gallery seed) |

### Valid skip reasons (v1 allowlist)

- `out_of_scope_for_surface` — e.g. inspiration on settings_form polish
- `user_directed_skip` — user said skip this family
- `blocked_external` — WAF/SSL/credentials; fallback already used
- `already_satisfied_by_code` — bound Spec / foundation already in repo artifacts
- `diminishing_returns` — strategy stop_conditions / polish_saturation soft|hard

Invalid / missing reason → item stays **open**.

### Recording skips / supersessions

- Store on PSM: `retry_counters["evidence_plan_status"][decision_id] = {state, reason, at, via_capability?}`
- Prefer recording via existing design_review dispositions or a small helper used by normalize when a stronger capability succeeds for the same decision_id
- Optional: agent passes skip through design_review / session metadata later; v1 can auto-supersede on known pairs and accept structured skip in ship dispositions only if cheap — otherwise compiler treats missing ledger + no skip as open

### Gate effect (design scopes only)

If any evidence-plan item is still **open** (not completed/skipped/superseded):

- Keep `claim_complete` in `prohibited_actions`
- Set `implementation_gate.evidence_plan_incomplete = true`
- `next_required_capability` = capability for highest-ROI open item (unless section/ship priority overrides)

**Do not** require running every capability on the plan — only that each item reaches a terminal state.

---

## 4. Residue scan (one pass max)

### When

On design-scope episodes, before Ship may clear **or** when ship would clear with `coverage == "thin"` / zero challenges despite dense UI:

1. If `residue_scan_completed` is already true → do not run again.
2. Else set `residue_scan_required = true`, prefer `next_required_capability = design_snapshot` (or observe) once.
3. After that snapshot/ship rebuild: emit residue challenges (uneven KPIs, settings measure/footer, etc.), set `residue_scan_completed = true`, clear `residue_scan_required`.

### Cap

**Exactly one** forced residue remeasure cycle per episode. After that, normal dispose/accept; polish_saturation and existing stop_conditions still apply. No recursive residue.

### Storage

`psm.episode.retry_counters["residue_scan"] = {required, completed, at}`

---

## 5. Initiative (advisory only)

```json
{
  "initiative": {
    "unpaid_families": [
      {"family": "component", "reason": "foundation undecided", "suggested": "perception_select_component_foundation"},
      {"family": "inspiration", "reason": "no usable reference", "suggested": "perception_inspiration_collect"}
    ],
    "note": "Advisory portfolio — not a gate. Skip with reason when ROI is low for this surface."
  }
}
```

- Helps agents see remaining intelligence **without** forcing calls.
- Must **not** add `claim_complete` prohibition by itself.
- May inform backlog ROI scores lightly (boost item if unpaid family maps to open structural decision).

---

## 5b. Episode Confidence (process completeness)

Computed each strategy refresh (not a gate). Surfaced on `engineering_strategy.episode_confidence`:

```json
{
  "score": 0.84,
  "band": "high",
  "contributors": [
    {"id": "spec_bound", "delta": 0.12, "detail": "Reference Spec bound"},
    {"id": "ship_clear", "delta": 0.15, "detail": "Ship Council clear"},
    {"id": "evidence_coverage", "delta": 0.18, "detail": "Evidence coverage 92%"},
    {"id": "residue_pending", "delta": -0.08, "detail": "Residue scan pending"},
    {"id": "inspiration_skipped", "delta": -0.02, "detail": "Inspiration skipped (valid reason)"}
  ]
}
```

**Rules:**
- Score clamped to `[0, 1]`; band: low &lt; 0.55, medium &lt; 0.8, else high.
- Positive contributors: verify passed, sections complete, ship clear, Spec bound, evidence-plan terminal coverage, snapshot coverage partial/full.
- Negative contributors: residue required, open backlog majors, thin ship coverage, open structural decisions.
- Valid skips are near-neutral (tiny negative or zero) — not punished like open gaps.
- Does **not** by itself prohibit `claim_complete`.

---

## 6. Implementation gate priority (updated)

For design-scope episodes:

1. Structural `blocked` (reference / foundation / system)
2. Section checklist incomplete
3. Residue scan required (once)
4. Ship council required
5. Evidence-plan open items (completed | skipped | superseded)
6. Ready (claim allowed if other flags clear)

Hotfix path unchanged: observe → fix → verify.

---

## 7. Extension points (code)

| Piece | Location |
|-------|----------|
| `surface_type` derive + sticky | `EpisodeState.surface_type` + `situation_policy` / `surface_type.py` |
| Backlog compile + ROI sort | new `planning/episode_backlog.py` called from `compile_engineering_strategy` |
| Evidence-plan terminal states | `implementation_readiness.py` + `retry_counters["evidence_plan_status"]` helpers |
| Residue cap | `retry_counters["residue_scan"]` + ship + readiness |
| Episode confidence | new `planning/episode_confidence.py` → strategy field only |
| Settings signals | `ship_council._collect_snapshot_signals` gated by `surface_type` |
| Initiative advisory | `engineering_strategy.py` (no gate coupling) |
| Methodology copy | `perception://engineering-strategy`, `perception://ship-council` |

## 8. Tests (minimum)

- Surface type from settings vs dashboard intent
- Settings measure / footer signals only when `settings_form`
- Backlog top = highest ROI among open items
- Evidence plan: completed / skipped(valid) / superseded allow claim; open blocks claim
- Invalid skip does not close item
- Residue required once then never again
- Initiative present but does not alone prohibit claim_complete
- Episode confidence score + contributors shape stable; valid skip ≠ large penalty
- Hotfix path unaffected
- `surface_type` lives on `EpisodeState`, not under `retry_counters`
## 9. Rollout

1. Spec approval (this doc)
2. Unit experiments (pure functions: surface derive, plan terminal, residue flag, backlog sort)
3. Wire into strategy + gate + ship
4. Methodology / rule template touch-ups
5. Preview package `1.2.0.dev11` (or next)

## 10. Out of scope follow-ups

- Auto UI for skip reasons in MCP UI hosts
- Multi-route residue matrix across all app pages in one pass
- LoopGovernor hard-stop on claim utterance (still no claim tool)
