# Verification subsystem

**Status:** ✅ shipped (evolving)

**Modules:** `mcp/handlers.py` (verify), `perception/observation.py`, `mcp/diff.py`

## Role

Verification is the **gate** for agent work: never claim UI done without `perception_verify`.

## Criteria types

| Type | Description |
|------|-------------|
| `url_contains` | Current URL substring |
| `text_contains` | Visible text |
| `js_assertions` | JS expressions returning truthy |
| (extensible) | New criteria via pydantic union |

## Failure behavior (v0.2+)

On failure:

1. Auto re-observe → `failure_scan_id`
2. Inline annotated screenshot in tool response
3. `data.failure` with criterion details

## Regression

`perception_diff` compares two `scan_id`s:

- Text / structural diff
- Visual diff (side-by-side + heatmap) when PNGs exist

## Agent playbook

See `AGENT_GUIDE.md` §2–§7:

1. OBSERVE → REASON → ACT → **VERIFY** → STOP
2. On verify fail: re-observe with screenshot → diff

## Future

- Criteria: `a11y_rule`, `network_status`, `console_clean` (post v0.4/v0.5)
- Batch verify for flow checkpoints

## Tests

`run_mcp_contract_tests.py` — `verify_negative` with inline image assertion
