# Agent-face no-guide E2E — coordination ladder (2026-07-28)

**Branch:** `exp/agent-face-simple`  
**Harness:** `scripts/eval_agent_face_no_guide_e2e.py`  
**Raw:** `docs/research/agent_face_no_guide_e2e.json`

## What “complete” means here

Card-only agent (no `resources/read` of guides/spines) can:

1. Bootstrap with intent  
2. Follow `agent_summary.card.next` + `next_args`  
3. Pay owed families without death-looping  
4. Reach `data.verified=true` on forms / hotfix / greenfield / redesign  

Ship council / full section checklist remain `claim_extra` when required — not skipped silently; `claim_ok` stays false until verify (+ extras).

## Face fixes landed

| Fix | Detail |
|-----|--------|
| `card.next_args` | Required args (esp. `query` for foundation select) filled from intent |
| Class owed priority | Greenfield: inspiration → LOOK → snapshot before component tunnel |
| Component tool align | `_FAMILY_TOOL["component"]` → `perception_select_component_foundation` |
| `claim_ok` | False until verify paid / `verification_status=passed` |
| Gate | `claim_complete` prohibited until verify passes (maintenance no longer false-green) |
| Component timeout | 35s (was 90s) so select cannot pin the process |
| Harness | Full ladder finishers; skip failing component after 1 fail |

## How to run

```powershell
# sandbox already on :18765
$env:PYTHONPATH="src"
python -u scripts/eval_agent_face_no_guide_e2e.py
```

BOARD fails if any case lacks `verified=true` on forms/hotfix/structural paths.

## Weakness pass (smart face)

| Weakness | Fix |
|----------|-----|
| Redesign skipped snapshot | `next_args.then` observe→snapshot; re-inject snapshot owed until paid |
| Gate bounced to `plan_component_search` | Empty owed climbs `verify`; plan demoted to select |
| `claim_extra` ignored | After verify passed → `design_review(mode=ship)` / sections |
| Follow rate ~0.75 | Redesign now follow **1.00** |

**Unit:** 17 passed · **BOARD:** PASS 4/4 · all classes follow=1.00 · greenfield next after select = `verify`
