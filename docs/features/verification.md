# Verification subsystem

**Status:** ✅ shipped (evolving)

**Modules:** `mcp/handlers.py` (verify), `perception/observation.py`, `mcp/diff.py`,
`coordination_intelligence/planning/section_checklist.py`

## Role

`perception_verify` proves **runtime criteria** (`data.verified`). It is necessary but
**not always sufficient** for claim-done.

Transport `ok=true` only means the tool call completed. Coordination uses
**`data.verified`** for `verification_status`.

### Done ladder (visual drafts)

1. Implementation readiness clear (or maintenance for hotfix)
2. Page verify with **`data.verified=true`**
3. Section checklist when `section_checklist_required` — observe → look →
   `perception_verify(section_id)` for each seeded layout block
4. Ship Council when `ship_council_required` —
   `perception_design_review(mode=ship)` → `ship_gate.council_clear`
5. Then claim-done

Hotfix / surgical: steps 3–4 skip.

## Criteria types

| Type | Description |
|------|-------------|
| `url_contains` | Current URL substring |
| `text_contains` | Visible text |
| `js_assertions` | JS expressions returning truthy |
| `section_id` | Optional; scopes assertions to a checklist block and marks that section verified |
| (extensible) | New criteria via pydantic union |

## Failure behavior (v0.2+)

On failure:

1. Auto re-observe → `failure_scan_id`
2. Inline annotated screenshot in tool response
3. `data.reasons` / feedback with criterion details
4. `data.verified=false` (envelope may still have top-level `ok=true`)

## Regression

`perception_diff` compares two `scan_id`s:

- Text / structural diff
- Visual diff (side-by-side + heatmap) when PNGs exist

## Agent playbook

See `AGENT_GUIDE.md` §0 and §19:

1. OBSERVE → REASON → ACT → **VERIFY** (`data.verified`) → section checklist / Ship Council when required → STOP
2. On verify fail: re-observe with screenshot → diff

## Future

- Criteria: `a11y_rule`, `network_status`, `console_clean` (post v0.4/v0.5)
- Batch verify for flow checkpoints

## Tests

`run_mcp_contract_tests.py` — `verify_negative` with inline image assertion  
`tests/test_section_checklist.py` — verified-vs-ok + section claim-complete gate
