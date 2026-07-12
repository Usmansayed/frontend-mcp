# Page Inspection Eval (E2E-2)

**Goal:** Prove a fresh agent session can inspect a page using AGENT_GUIDE section 2 alone, with independent verify and a before/after diff.

**Prerequisites:**
- Sandbox dev server: `cd sandbox && npm run dev` (default `http://localhost:5173`)
- Frontend Perception MCP connected

---

## Task (give this to the agent)

> Using the Frontend Perception MCP, inspect the sandbox home page (`/`) and confirm it renders cleanly. Follow AGENT_GUIDE section 2. Do not claim done without `perception_verify`.

---

## Expected agent behavior (checklist)

| Step | Tool | Pass criteria |
|------|------|---------------|
| 1 | `perception_health` | `ok: true` |
| 2 | `perception_session_start` | `session_id` returned |
| 3 | `perception_navigate_and_observe` → `/` | `scan_id` saved; `agent_summary.blocking` empty |
| 4 | `perception_verify` | URL contains `/`; `verified: true` |
| 5 | `perception_observe` (again) | second `scan_id` for diff |
| 6 | `perception_diff` | diff computed successfully |
| 7 | `perception_session_end` | session cleaned up |

---

## Failure signals

- Agent claims done without `perception_verify`
- `agent_summary.blocking` non-empty on final observe
- Any MCP response contains planning hints like "you should next..."

---

## Automated golden path

```bash
$env:PYTHONPATH="src"
python src/run_mcp_eval_page_inspection.py --headless
```

Emits `artifacts/evals/E2E-2/report.json` with the full trace.
