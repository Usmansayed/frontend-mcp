# Code ↔ UI Correlation Eval (E2E-10)

**Goal:** Prove that the agent can correlate `perception_code_context` output with `perception_navigate_and_observe` on the same route — AGENT_GUIDE section 10.

**Prerequisites:**
- Sandbox dev server
- Frontend Perception MCP connected

---

## Task (give this to the agent)

> Use `perception_code_context` on the sandbox repo to locate the component that renders `/forms/validation`, then observe the running page. Confirm the route resolves and the DOM contains the expected form. Follow AGENT_GUIDE section 10.

---

## Expected agent behavior

| Step | Tool | Pass criteria |
|------|------|---------------|
| 1 | `perception_health` | `ok: true` |
| 2 | `perception_code_context` (stats) | repo stats returned |
| 3 | `perception_code_context` (get_route) | route entry present or explicit `degraded[]` |
| 4 | `perception_session_start` | `session_id` returned |
| 5 | `perception_navigate_and_observe` → `/forms/validation` | `Validated form` in DOM |
| 6 | `perception_verify` | URL contains `/forms/validation`; `verified: true` |
| 7 | `perception_observe` (summary_only) | `agent_summary.blocking` empty |
| 8 | `perception_session_end` | cleaned up |

---

## Automated golden path

```bash
$env:PYTHONPATH="src"
python src/run_mcp_eval_code_ui.py --headless
```

Emits `artifacts/evals/E2E-10/report.json`.
