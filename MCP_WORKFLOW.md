# Frontend Perception MCP Workflow

This explains how we use an **AI coding agent** as the brain while keeping MCP deterministic (no LLM in MCP).

## Short Answer

Yes, this part is already designed and implemented.

- **AI Agent (Cursor/Claude/Codex):** planning, reasoning, code edits, deciding next step
- **Frontend Perception MCP:** deterministic runtime for browser observation + actions + verification
- **No LLM inside MCP:** MCP only executes typed tools and returns structured facts

---

## Why Agent Instead of LLM Inside MCP

We intentionally separated concerns:

1. **Planning belongs to the host agent**
   - The host agent already has task context, repo context, and user intent.
   - It decides strategy and whether to edit code, run a probe, or verify.

2. **Execution belongs to MCP**
   - MCP handles deterministic operations: navigate, observe, execute script/actions, verify, probe forms/guards, state save/restore.
   - MCP responses are factual JSON (no "you should next..." guidance).

3. **Result**
   - Model-agnostic workflow (works with different coding agents/models).
   - Lower cost and simpler infrastructure than embedding another LLM in runtime.
   - Better debuggability because every step is explicit and typed.

---

## Runtime Architecture

```text
Host AI Agent (brain)
  ├─ reads AGENT_GUIDE playbooks
  ├─ reasons on MCP outputs
  └─ edits repo / calls MCP tools
         │
         ▼
Frontend Perception MCP (deterministic runtime)
  ├─ session store
  ├─ scan registry
  ├─ tool handlers
  └─ resource handlers
         │
         ▼
BrowserSession (browser-use + CDP) -> Chromium
```

---

## Behavior Programming (How Agent Is Guided Without MCP LLM)

We "program" behavior through three layers:

1. **`AGENT_GUIDE.md` (primary contract)**
   - Playbooks by task type (page inspection, debugging, forms, routing, flows, regression, responsive, edge cases, code↔UI).

2. **MCP `instructions`**
   - Session preamble enforces universal loop and hard rules.
   - Points agent to `AGENT_GUIDE.md` and MCP resources.

3. **Tool descriptions + schemas**
   - Each tool description references when to use it in playbooks.
   - Schemas make calls typed and predictable.

This gives us behavior control **without** putting planning logic into server responses.

---

## Universal Agent Loop

Every frontend task follows:

1. **OBSERVE**
   - `perception_navigate_and_observe` or `perception_observe` (save `scan_id`)
2. **REASON**
   - Agent reads `agent_summary.blocking` first, then advisory + DOM/dev insights
3. **ACT**
   - Edit code and/or call `perception_execute_script` / `perception_execute_actions`
4. **VERIFY**
   - `perception_verify` (never skip after ACT)
5. **DECIDE**
   - Pass: done/next step
   - Fail: re-observe + `perception_diff`, then loop

Hard stop: if `perception_auth_gate` returns `requires_human: true`, agent asks user.

---

## MCP Tool Categories

- **Lifecycle:** `perception_health`, `perception_session_start`, `perception_session_end`
- **Observe:** `perception_navigate`, `perception_navigate_and_observe`, `perception_observe`
- **Act:** `perception_execute_script`, `perception_execute_actions`
- **Verify/Compare:** `perception_verify`, `perception_diff`
- **Specialized probes:** `perception_probe_form`, `perception_probe_guards`, `perception_auth_gate`
- **State/flows/context:** `perception_state_save`, `perception_state_restore`, `perception_state_list`, `perception_flow_describe`, `perception_code_context`

All tools return the envelope (`contract_version`, `ok`, `scan_id`, `error`, `degraded`, `data`).

---

## Resources (M4)

Static resources:
- `perception://agent-guide`
- `perception://eval/validation-form`

Dynamic scan resources:
- `perception://scan/{scan_id}/report.json`
- `perception://scan/{scan_id}/screenshot.png`

Resource payload behavior:
- `report.json` returns JSON text
- `screenshot.png` returns `image/png` blob payload (base64 in MCP blob resource content)

Also supported on observe tools:
- `detail: "full"` (default full observation payload)
- `detail: "summary_only"` (compact payload with `agent_summary`)

---

## What MCP Must Never Do

- No autonomous planning
- No natural-language task execution API
- No "next action" recommendations in responses
- No hidden decision-making

MCP is execution + observation infrastructure; the host agent remains the decision-maker.

---

## Verification Status

Current checks proving this workflow:

- `python src/run_mcp_contract_tests.py` (contract/tool behavior)
- `python src/run_mcp_eval_validation_form.py` (playbook-driven eval)
- `python src/run_all_phases.py` (end-to-end phases + MCP checks)

## Distribution

- Script entrypoint: `frontend-perception-mcp`
- Module entrypoint: `python -m navigation.mcp`
- `uvx` usage: `uvx --from frontend-perception-engine frontend-perception-mcp`

If these pass, we have a working "agent-as-brain, MCP-as-runtime" system.
