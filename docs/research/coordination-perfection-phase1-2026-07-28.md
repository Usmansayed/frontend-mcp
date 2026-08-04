# Coordination perfection — Phase 1 evidence (2026-07-28)

**Program:** `docs/superpowers/specs/2026-07-28-coordination-perfection-design.md`  
**Plan:** `docs/superpowers/plans/2026-07-28-coordination-perfection-phase1.md`

## Pass bar

| Gate | Result |
|------|--------|
| Adversarial card unit + bootstrap | **31 passed** |
| No-guide E2E BOARD | **PASS 4/4** (~39s) |
| P0 G1–G3 closed | **yes** |

## P0 fixes shipped

| ID | Change |
|----|--------|
| G1 | Empty owed + verify passed + no `claim_extra` → `next=""` (no re-spine). Promote always syncs `recommended_next` to `card.next` (including empty). |
| G2 | `_claim_ok` false whenever `_claim_extra` non-empty |
| G3 | Polish/chrome cues + `right_sizing.tier` in {polish,touch_up} classify as `hotfix` before `design_driven`→greenfield |

## P1 locks also shipped

- Feature excludes inspiration from owed; finish never invents inspiration
- Section / ship / spec revision next + claim_ok false
- `plan_component_search` remapped to select in owed + next
- Reference-image / figma cues → redesign
- Spec-revision snapshot skips observe bridge when already verified
- Instructions: empty `next` + `claim_ok` → stop and claim

## Remaining (Phase 1 defer → Phase 2/3)

- G6 fix∩feature classifier edge cases (partial)
- G9 polish tier VF on hotfix finish (depth=standard but hotfix finish branch still observe+verify only)
- G13 forms keyword over-capture on landing+signup
- Human A/B (Phase 2)
- Latency/soak (Phase 3)

## Artifacts

- `tests/test_coordinator_card.py` (expanded)
- `docs/research/agent_face_no_guide_e2e_phase1.json`
- Code: `coordinator_card.py`, `engineering_strategy.py`, `instructions.py`
