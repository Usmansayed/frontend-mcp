# Validation Form Eval (M3)

**Goal:** Prove a fresh agent session can complete frontend form work using **AGENT_GUIDE §4** only — the MCP must not suggest next steps.

**Prerequisites:**
- Sandbox dev server: `cd sandbox && npm run dev` (default `http://localhost:5173`)
- Frontend Perception MCP connected (see `MCP_PLAN.md` §5.1)

---

## Task (give this to the agent)

> Using the Frontend Perception MCP, verify the sandbox validation form at `/forms/validation` works correctly: invalid submit shows validation errors, valid submit shows success. Follow AGENT_GUIDE §4. Do not claim done without verify.

---

## Expected agent behavior (checklist)

The agent should call tools in roughly this order. Deviations are OK if verify still passes and playbooks are followed.

| Step | Tool | Pass criteria |
|------|------|---------------|
| 1 | `perception_health` | `ok: true` |
| 2 | `perception_session_start` | `session_id` returned |
| 3 | `perception_navigate_and_observe` → `/forms/validation` | `scan_id` saved; `Validated form` in observation |
| 4 | `perception_probe_form` | `probe.ok: true`; rules extracted |
| 5 | `perception_execute_actions` → click `Validate & submit` (empty form) | action succeeds |
| 6 | `perception_verify` | `text_contains: ["Invalid email"]` → `verified: true` |
| 7 | `perception_execute_actions` → fill Email, Phone, Age, terms + submit | all actions `ok: true` |
| 8 | `perception_verify` | `text_contains: ["Form is valid"]` → `verified: true` |
| 9 | `perception_observe` + `perception_diff` (optional) | no new blocking issues |
| 10 | `perception_session_end` | session cleaned up |

---

## Valid fill values (sandbox)

| Field | Value |
|-------|-------|
| Email | `test@example.com` |
| Phone | `1234567890` |
| Age | `25` |
| Terms | checked |

Submit button label: **Validate & submit**

---

## Failure signals

- Agent claims done without `perception_verify`
- Agent skips `perception_probe_form`
- Agent loops login (N/A for this form — but `perception_auth_gate` should not block)
- MCP response contains planning hints like "you should next…" (contract violation)
- `agent_summary.blocking` non-empty on final observe

---

## Automated golden path

CI runs the same playbook without an LLM:

```bash
$env:PYTHONPATH="src"
python src/run_mcp_eval_validation_form.py
```

Pass = agent wiring is correct; use the manual task above to validate a real Cursor session.
