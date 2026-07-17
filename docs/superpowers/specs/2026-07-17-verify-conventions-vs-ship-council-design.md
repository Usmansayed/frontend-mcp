# Verify Conventions vs Ship Council

**Date:** 2026-07-17  
**Status:** Approved (user refinement)

## Problem

Soft `perception_verify` (URL/text criteria) can pass while objective UX engineering flaws remain — e.g. a dashboard sidebar that scrolls with content. Ship Council can detect `nav_not_sticky`, but agents skip ship mode after polish/maintenance collapse and report “everything passed.” Gates that never fail on broken chrome make the MCP feel useless.

## Split (source of truth)

| Layer | Role | Examples |
|-------|------|----------|
| **Verify** | Objective, measurable engineering conventions. Deterministic JS / layout facts. Fail → `data.verified=false` → claim-done blocked. | Sticky/fixed dashboard sidebar or primary nav chrome; horizontal overflow; missing region presence/size; a11y blockers already in observe |
| **Ship Council** | Subjective but high-ROI design decisions. Challenges → revise / accept-with-rationale / ask_user. | Hierarchy / equal-weight KPIs; composition; narrow centered product shells; theme coupling; Spec drift |

Do **not** pack subjective design heuristics into verify.

## Verify conventions (v1)

Injected automatically on `perception_verify` when the episode is design-driven / redesign / system_setup **and** a design snapshot exists (or section checklist includes chrome roles):

1. **Chrome permanence** — For `aside` / `nav` / `sidebar` / primary navigation regions: element (or an ancestor) must have `position: sticky|fixed`.
2. **Horizontal overflow** — `documentElement.scrollWidth <= innerWidth + tolerance`.
3. **Section presence** (existing) — Region exists and has non-trivial box.

Section checklist verify continues to inject role-scoped asserts; page-level soft verify also receives chrome conventions so agents cannot bypass by omitting `section_id`.

Hotfix / surgical / debug scopes skip chrome convention injection (surgical verify stays criteria-only).

## Ship Council (after conventions)

- Remove snapshot-driven **`nav_not_sticky`** and **`responsive_breakage`** from Ship Council signal collection (those are verify’s job).
- Keep ROI challenges: hierarchy, composition, narrow centered main, theme coupling, Spec drift, brand ask-user.
- Still required after page verify pass + snapshot on design/redesign episodes (sticky design scope preserved).

## Seeding

Seed section checklist on **both** reference-bind and current snapshot paths so redesign episodes always get chrome sections to verify.

## Success criteria

- Soft verify on a dashboard with a static/scrolling sidebar → `verified=false` with an explicit chrome permanence reason.
- After sticky fix → verify can pass; Ship Council still challenges hierarchy/composition, not “is the sidebar sticky?”
- Meridian-class “everything passed with scrollable sidebar” is no longer possible without ignoring `data.verified`.
