# Flaky evaluation failures — investigation (v1.1.5)

**Date:** 2026-07-13  
**Scope:** Three edge-lab contract tests that intermittently failed before v1.1.5.

## Tests

| Test | Symptom |
|------|---------|
| `console_observe` | No `EDGE_LAB_CONSOLE_ERROR` in observation |
| `network_observe_failure` | No 404 / `failed_count` for dev-insights-missing |
| `network_observe_slow` | No slow request capture on devtestb |

## Verdict: evaluator / harness issues (not tool regressions)

All three failures traced to **test harness assumptions**, not broken MCP handlers.

### 1. `console_observe` and `network_observe_failure`

**Root cause:** Contract tests called `handle_navigate_and_observe` without `detail: "full"`.  
Default `summary_only` omits the full `observation` object (by design). Tests read `observation.console` / `observation.network` directly and saw empty data even when `agent_summary` was correct.

**Fix:** Pass `detail: "full"` in `src/run_mcp_contract_tests.py` and `scripts/test_edge_lab_only.py`.

### 2. `network_observe_failure` (ordering)

**Root cause:** Test re-navigated to the same `/edge-lab?devtest=1` URL. React SPAs do not re-fetch on identical navigation, so the 404 request never fired again.

**Fix:** Reuse the first `devtest=1` observation for network failure assertions instead of a second navigate.

### 3. `network_observe_slow`

**Root cause:** Edge-lab collector signals (console/network) are emitted asynchronously after paint. `collect_observation` snapshot ran before SPA hooks completed.

**Fix:** `wait_for_edge_lab_collector_signals()` in dev insights, called from observation collection before snapshot.

## Validation

- Local contract suite: **77/77 PASS** after fixes (v1.1.5).
- Dedicated script `scripts/test_edge_lab_only.py` encodes the three tests with correct arguments.
- Installed PyPI eval: contract step **74/74 PASS** in v1.1.5 agent battery.

## Not flaky tool behavior

- `perception_navigate_and_observe` correctly omits `observation` in `summary_only`.
- Console/network CDP capture works when `detail: full` is requested.
- Edge-lab signals require a short wait — documented in AGENT_GUIDE §1b.

## Agent guidance (no new coordinator)

Evaluators and agents should:

1. Use `detail: "full"` when asserting on `observation.console` / `observation.network`.
2. Prefer `agent_summary` for first-pass blocking checks.
3. Not re-navigate to the same SPA URL when testing network side effects.
