# Frontend MCP redesign — inspiration-heavy look & feedback

**Date:** 2026-07-27  
**Parent:** [2026-07-26-inspiration-first-design-loop.md](../plans/2026-07-26-inspiration-first-design-loop.md)  
**Status:** research + redesign direction (build Phase 1 next)

---

## 1. What we already proved

| Piece | State |
|-------|--------|
| Thesis: agents copy-adapt better than invent | Confirmed in parent plan |
| Inspiration speed (HTTP concurrent, levels, no WAF hang on wide) | Shipped |
| Levels as **agent-chosen effort** (light/standard/wide/max) | Shipped — soft-stop, **no hard ref cap** |
| `visual_feedback(purpose=inspiration)` borrow/ignore | Exists; under-used as “direction paid” |

The remaining gap is **product behavior**: coordination and feedback still let greenfield skip the creative spine or treat inspiration as optional ops.

---

## 2. Redesign north star

> **Frontend MCP is an inspiration → look-lock → implement → LOOK-against-refs product.**  
> Perception proves. It does not invent taste.

### Agent framework (keep short — not a ceremony layer)

Give the agent **how to think** and **a few soft choices**. We execute budgets.

| Decision | Soft choices | Agent rule |
|----------|--------------|------------|
| How hard to hunt refs | `light` \| `standard` \| `wide` \| `max` | Pick from task context; not a ref quota |
| Did we lock a look? | borrow/ignore via VF inspiration | Collect alone ≠ direction paid |
| Draft vs refs | VF design + compare checklist | Don’t invent a third aesthetic |
| Scope | greenfield / redesign / polish / hotfix | Only greenfield gets full spine |

No huge coordination docs. Situation cards + `perception://guide/inspiration` + greenfield card.

---

## 3. Inspiration-heavy feedback (“look design”)

### Today

`purpose=inspiration` asks for `borrow` / `ignore` after LOOK. Next actions still often push “collect more” or generic design.

### Target feedback contract

After refs are visible, one judgment should produce a **machine-usable look lock**:

```json
{
  "judgment": "revise",
  "borrow": ["full-bleed product hero", "single CTA group", "editorial serif display"],
  "ignore": ["their pricing grid", "dark purple glow"],
  "look_lock": {
    "composition": "one first-viewport composition, brand-first",
    "hierarchy": "brand > headline > one line > CTA",
    "density": "air / marketing",
    "type_mood": "expressive serif + quiet sans",
    "chrome": "minimal nav, no card hero",
    "motion": "2–3 intentional entrances"
  },
  "primary_ref_ids": ["hit_0", "hit_2"]
}
```

**Advancement:** `look_lock` (or non-empty `borrow`) + at least one looked ref → `inspiration_extract` paid.

**Next actions (advisory):** `implement_from_borrow` first — not another collect — unless agent marks pack weak.

### Draft compare (purpose=design, inspiration-bound)

When a seed Spec / ref pack is bound:

- Extra keys: `vs_inspiration` — `{match: [...], drift: [...], fix_toward_refs: [...]}`  
- Hard fail language: “new palette mid-episode with bound refs”

---

## 4. Coordination redesign (Phase 1 — highest ROI)

Align unpaid spine with parent plan §6, but **light**:

```text
greenfield / design_driven, no mockup:
  1. inspiration_collect (+ level)
  2. inspiration_extract  ← visual_feedback(purpose=inspiration) look_lock
  3. implement (component only if needed)
  4. observe + visual_feedback(purpose=design) vs refs
  5. consistency (after look locked + draft LOOK)
  6. verify (+ compare-to-refs signal)
```

| Change | Detail |
|--------|--------|
| Gate order | Inspiration before snapshot/foundation for invent-from-scratch |
| Extract required | Collect alone does not clear “direction” unpaid |
| Snapshot | Skip/supersede only with reason (user mockup / live measure) |
| Guides | Short greenfield + inspiration levels; hard-fail “invented UI, no refs” |
| Right-sizing | Polish/hotfix stay light — no full spine |

Do **not** rebuild a heavy ceremony engine. Prefer: unpaid list + `recommended_resource` + one levels card.

---

## 5. Tool / surface changes (build order)

1. **Docs/cards** — greenfield + hard-fails + inspiration levels (soft choices) ✅ levels card started  
2. **VF inspiration** — `look_lock` schema + next_actions → implement_from_borrow  
3. **Coordination unpaid order** — inspiration → extract before foundation  
4. **Bind refs** — collect → seed Spec / primary_ref_ids stick to episode  
5. **Design VF** — `vs_inspiration` when bound  
6. **Optional** — `perception_inspiration_extract` thin alias that *is* VF inspiration (same runner)

---

## 6. Open decisions (lock before coding Phase 1)

1. Is VF inspiration enough for extract unpaid, or alias tool for clarity? **Recommend:** same runner, unpaid family `inspiration_extract`.  
2. Soft-stop defaults (4/8/12/16) — agent override via `target_refs`. **No hard cap** ✅  
3. Live competitor snapshot counts as inspiration-equivalent? **Yes** (existing live_site / supersede).  
4. How strict is “compared to inspiration” on Done ladder? **Recommend:** checklist item for design_driven, not full Ship Council always.

---

## 7. What “redesign Frontend MCP” means here

Not a rewrite of the browser runtime. It means:

- **Product spine** = inspiration-first look lock  
- **Agent UX** = soft levels + short guides + VF that forces borrow/look_lock  
- **Coordination** = unpaid order that matches the spine  
- **Perception** = prove draft against refs and standards  

Inspiration engine work (speed/reliability/levels) is the enabler. Phase 1–4 of the parent plan are the redesign.

---

## 8. Suggested next build session

1. Ship soft-stop / no-hard-cap + guide copy (this pass).  
2. Extend `visual_feedback` inspiration schema with `look_lock` + next_actions.  
3. Wire coordination unpaid: inspiration → extract before foundation.  
4. Update `perception://guide/greenfield` + hard-fails one-liners.  
5. Smoke: greenfield episode shows extract unpaid after collect; draft VF shows `vs_inspiration` when bound.
