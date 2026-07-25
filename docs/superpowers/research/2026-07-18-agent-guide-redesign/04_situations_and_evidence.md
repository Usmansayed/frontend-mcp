# 04 — Situations and Minimum Evidence

## Task scopes (code)

**Source:** `situation_policy._derive_task_scope`

| Scope | Typical signals |
|-------|-----------------|
| `hotfix` | situation hotfix, “hotfix”, incident/sev |
| `system_setup` | design system, token, foundation, theme setup |
| `redesign` | redesign, rebrand |
| `design_driven` | new landing, marketing site, homepage hero, landing/new dashboard, inspiration_needed |
| `surgical` | padding/margin/tweak/one button/… (or sticky design + those keywords) |
| `debug` | bug / functional_bug / debug cluster (non-sticky) |
| `feature_incremental` | default |

**Sticky design:** once `design_driven` / `redesign` / `system_setup`, episode remembers via `episode_design_scope` so verify-fail doesn’t erase Done-ladder obligations — unless explicit bug intent.

### Agent-facing class names (guides should use)

Map code scopes → simple classes agents classify:

| Agent class | Maps from |
|-------------|-----------|
| `greenfield` | design_driven (no existing mockup) |
| `redesign` | redesign, rebrand, visual overhaul |
| `mockup` | redesign/design_driven + user reference image/Figma target |
| `feature` | feature_incremental |
| `hotfix` | hotfix, debug (symptom-led) |
| `polish` | surgical / soft visual tweak |
| `forms` / `guards` | form/flow intents (probe tools) |

---

## Surface types (code)

**Source:** `surface_type.derive_surface_type`

Affects Ship Council signals (e.g. equal-KPI on dashboard, not settings).

Examples: `dashboard`, `settings_form`, `auth`, `marketing`, `mixed`, `unknown`.

**Guide note:** Agents don’t need full taxonomy; they must know ship challenges differ by surface — don’t “fix” settings with dashboard KPI rules.

---

## Influence levels (agent rule)

| Level | Behavior |
|-------|----------|
| structural | Evidence before large code |
| balanced | Evidence → implement → verify → ladder |
| minimal / maintenance | Observe → fix → verify; no insp/redesign unless sticky design draft |

---

## Minimum evidence paths (synthesis: rule §5 + methodology + portfolio)

### Greenfield / design_driven
1. Bootstrap + strategy  
2. Reference: inspiration **or** figma **or** snapshot  
3. Component foundation if unpaid  
4. Observe baseline  
5. Draft  
6. Remeasure / SpecDiff  
7. Verify → sections → ship if gated  

**Skip:** SEO, ritual insp loops, deep consistency before first draft.

### Redesign (no mockup)
1. Observe current  
2. Snapshot (bind)  
3. SpecDiff / design review as needed  
4. Code  
5. Remeasure → verify → ladder  

**Inspiration:** only if direction still open (`design_reference_posture=none` and no mockup).

### Mockup / uploaded reference
1. Correct port/app observe  
2. **Snapshot bind** (primary) — not gallery inspiration  
3. Foundation if unpaid  
4. Draft vs Spec  
5. SpecDiff → hard verify → ladder  

### Feature
1. Observe affected routes  
2. `resolve_*` if owners unclear  
3. Implement  
4. Verify (`data.verified=true`)  
5. Ladder only if gate flags  

**Skip:** greenfield inspiration, new foundation unless unpaid and truly needed.

### Hotfix / debug
1. Observe (**blocking** first)  
2. Smallest fix  
3. Verify symptom  
4. Diff on fail  

**Skip:** inspiration, foundation, ship, checklist — unless structure reopened / sticky design.

### Polish / surgical
Same as hotfix with **hard CSS criteria**; watch overlays.

**Exception:** If this episode already drafted design_driven UI, finish checklist + ship.

### Forms / guards / flows
`probe_form` / `probe_guards` / flow checkpoints + strategy; don’t treat greenfield landing as “just a form.”

---

## Classification pitfalls (for guides)

1. User says “make it professional” on existing page → often **redesign**, not polish.  
2. User says “reduce blur 20%” after redesign → **polish**, don’t reopen foundation.  
3. User attaches screenshot → **mockup**, not inspiration gallery.  
4. Sticky design episode + tiny tweak → may still owe ship if draft was design_driven — call out exception carefully.  
5. **Empty unpaid** (outside design initiative) → still run class min path; don’t treat empty as “nothing to do.”  
6. Gate says SHIP while snapshot unpaid → pay structural unpaid first (ladder does not erase reference debt).
