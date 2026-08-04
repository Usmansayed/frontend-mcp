# Coordination perfection Phase 1 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close P0 card gaps G1–G3 and lock P1 adversarial matrix; keep no-guide BOARD green.

**Architecture:** Only `build_agent_face_card` / helpers in `coordinator_card.py` change. Tests in `tests/test_coordinator_card.py`. Docs under `docs/superpowers/` + `docs/research/`.

**Tech stack:** Python, pytest.

---

### Task 1: Failing P0 tests

**Files:**
- Modify: `tests/test_coordinator_card.py`

Add:
1. `test_face_done_state_does_not_respine` — forms + hotfix after verify passed, unpaid=[], no claim_extra → `claim_ok` True, `next == ""`
2. `test_face_claim_ok_false_when_claim_extra_even_if_gate_allows` — ship required, prohibited=[], verify passed → `claim_ok` False, next design_review
3. `test_face_polish_not_greenfield_under_design_driven` — polish navbar + design_driven + tier polish → class hotfix, depth ≠ full (or finish skips inspiration)

Also update `test_promote_surfaces_agent_summary_card` expectations for empty next.

**Run:** `pytest tests/test_coordinator_card.py -q` → expect new fails.

### Task 2: Implement G1–G3

**Files:**
- Modify: `src/navigation/coordination_intelligence/planning/coordinator_card.py`

1. `_pick_class_next`: after claim_extra ladder, if verify passed and not extra → return `""`
2. `_claim_ok`: if `_claim_extra(...)` non-empty → False
3. `classify_agent_face`: polish cues + right_sizing.tier=polish before design_driven → hotfix

**Run:** unit tests pass.

### Task 3: P1 matrix tests (lock or fix)

Add feature / section / spec / plan-as-suggested / mockup soft cues tests. Fix only if cheap; else mark xfail with ticket note in research doc.

### Task 4: Evidence + no-guide board

- Write `docs/research/coordination-perfection-phase1-2026-07-28.md`
- Run `python scripts/eval_agent_face_no_guide_e2e.py` (or BOARD subset)
- Confirm unit board green

### Task 5: Commit (only if user asks)

Do not commit unless requested.
