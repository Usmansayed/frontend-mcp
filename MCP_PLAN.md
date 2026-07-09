# Frontend Perception MCP — Build Plan

**Status:** Engine phases 1–4 + hardening complete. **M1–M4 MCP shipped** (see §5.1–5.4).

This document is the **north star**. When scope drifts, return here.

Companion explainer: [`MCP_WORKFLOW.md`](MCP_WORKFLOW.md) (agent-as-brain workflow and MCP operation).

---

## 1. What we are building

A **free, deterministic Frontend Perception MCP** that coding agents (Cursor, Claude Code, etc.) use as a **browser runtime and observation layer**.

| Layer | Owner | Role |
|-------|--------|------|
| **Brain** | Host coding agent | Plans, reasons, writes code, decides what to do next |
| **Runtime** | Our MCP | Navigate, observe, execute scripts, verify — **no LLM** |
| **Driver** | `browser-use` `BrowserSession` | Chromium + CDP |

We are **not** building an autonomous browser agent as the primary product.  
We **are** building the protocol + tools that make the **host agent** an effective navigator.

The MCP does not lack a brain — **the agent is the brain**. Since there is no LLM inside the MCP, we **program the host agent's behavior** through:

- **Playbooks** in [`AGENT_GUIDE.md`](AGENT_GUIDE.md) — workflows per task type (not API docs)
- **Tool descriptions** in the MCP manifest — when to use each tool in context of playbooks
- **MCP server `instructions`** — short behavioral preamble injected every session

A new agent should connect once, read the guide, and naturally follow **observe → reason → act → verify** without any planning logic in the server.

---

## 2. What we are NOT building

- No LLM inside the MCP (no OpenAI, Bedrock, or `browser_use.Agent` in the default path)
- No natural-language task APIs (`run_task("fix checkout")`)
- No “suggested next action” or planning inside MCP responses
- No stripping of engine features — all perception capabilities become **typed tools**

**Optional (secondary):** `PerceptionAgentRunner` + Bedrock remains a separate autonomous demo path, not the free MCP product.

---

## 3. Architecture

```text
┌─────────────────────────────────────────────────────────┐
│  HOST AGENT (Cursor / Claude / …)          = BRAIN      │
│  - follows MCP contract + AGENT_GUIDE rules             │
│  - plans loop: observe → act → verify → repeat          │
└──────────────────────────┬──────────────────────────────┘
                           │ structured JSON tool calls
                           ▼
┌─────────────────────────────────────────────────────────┐
│  frontend-perception MCP                   = RUNTIME    │
│  SessionStore · scan registry · tool handlers           │
│  wraps: navigation/perception/* (existing engine)       │
└──────────────────────────┬──────────────────────────────┘
                           │ BrowserSession (CDP)
                           ▼
                      Chromium
```

**Optional sidecar:** `perception_code_context` → CRG (`navigation/codeGraph/`) for static hints. No LLM required.

---

## 4. Already built (engine — do not re-litigate)

| Area | Modules | Verified by |
|------|---------|-------------|
| Observation + verify | `observation.py`, `verification.py` | `run_phase1.py` |
| Dev insights Tier A/B | `dev_insights.py`, `cdp_hub.py` | `run_phase1.py` |
| Auth gate | `auth_gate.py` | Phase 1 |
| Form probe | `form_probe.py` | Phase 1 |
| State + cookies | `state_manager.py` | `run_hardening.py` |
| Route guards | `route_guards.py` | `run_phase2.py` |
| Flow graph | `flow_graph.py`, `runner.py` | `run_phase3.py` |
| Edge cases | exploration, iframe, upload, … | `run_phase4.py` |
| Unified scan | `scan.py` | `run_hardening.py` |
| Preflight + waits | `preflight.py` | Hardening |
| Token budget | `budget.py` | Observation output |
| Hardening | hub, dedup, cookies | `run_hardening.py` |

```bash
cd sandbox && npm run dev
$env:PYTHONPATH="src"
python src/run_all_phases.py   # phases 1–4 + hardening
```

**Rule:** New work **wraps** this engine in MCP tools; do not fork perception logic into the MCP layer.

---

## 5. What we build from now on

### 5.1 MCP core (Milestone M1) ✅

| Deliverable | Status |
|-------------|--------|
| `src/navigation/mcp/` | ✅ `server.py`, `handlers.py`, `session_store.py`, `scan_registry.py`, `envelope.py` |
| `SessionStore` | ✅ |
| `ScanRegistry` | ✅ |
| `Envelope` + `agent_summary` | ✅ |
| MCP stdio entry | ✅ `python -m navigation.mcp` / `frontend-perception-mcp` |
| **Tools (M1)** | ✅ health, session_start/end, navigate_and_observe, verify, execute_script |
| Contract tests | ✅ `python src/run_mcp_contract_tests.py` |

**Cursor config example:**

```json
{
  "mcpServers": {
    "frontend-perception": {
      "command": "python",
      "args": ["-m", "navigation.mcp"],
      "env": {
        "PYTHONPATH": "C:/Users/usman/Projects/frontend-perception-engine/src"
      }
    }
  }
}
```

Read `AGENT_GUIDE.md` in the project — MCP `instructions` point agents to the playbooks.

### 5.2 Full tool surface (Milestone M2) ✅

| Deliverable | Status |
|-------------|--------|
| `tools.py` | ✅ Tool schemas + playbook descriptions |
| `diff.py` | ✅ Compare two `scan_id` observations |
| **Tools (M2)** | ✅ navigate, observe, execute_actions, diff, auth_gate, probe_form, probe_guards, state_save/restore/list, flow_describe, code_context |
| Contract tests | ✅ `run_mcp_contract_tests.py` — 20 cases (M1 + M2) |

Engine mapping:

| Tool | Engine source |
|------|----------------|
| `perception_navigate` | `preflight.py` |
| `perception_observe` | `collect_observation()` |
| `perception_execute_actions` | `scripted_actions.py` |
| `perception_diff` | `mcp/diff.py` |
| `perception_auth_gate` | `auth_gate.py` |
| `perception_probe_form` | `form_probe.py` |
| `perception_probe_guards` | `route_guards.py` |
| `perception_state_save/restore/list` | `state_manager.py` |
| `perception_flow_describe` | `flow_graph.FLOWS` |
| `perception_code_context` | `codeGraph` (optional) |

### 5.3 Agent behavior program (Milestone M3) ✅

| Deliverable | Status |
|-------------|--------|
| [`AGENT_GUIDE.md`](AGENT_GUIDE.md) | ✅ Primary contract — playbooks per task type |
| MCP tool `description` fields | ✅ Tied to AGENT_GUIDE sections in `tools.py` |
| MCP server `instructions` | ✅ Full playbook map + hard rules in `instructions.py` |
| MCP resources | ✅ `perception://agent-guide`, `perception://eval/validation-form` |
| `.cursor/rules/frontend-perception-mcp.mdc` | ✅ Enforce observe → act → verify |
| Eval scenario | ✅ `evals/VALIDATION_FORM_EVAL.md` + `run_mcp_eval_validation_form.py` |

**Done when:** A fresh Cursor session with MCP + `AGENT_GUIDE.md` completes the validation-form eval using the form playbook, without MCP suggesting next steps.

**Automated golden path:** `python src/run_mcp_eval_validation_form.py`

**Manual eval task:** See `evals/VALIDATION_FORM_EVAL.md` or MCP resource `perception://eval/validation-form`.

### 5.4 Resources & polish (Milestone M4) ✅

| Deliverable | Status |
|-------------|--------|
| MCP resources | ✅ `perception://scan/{scan_id}/report.json` + `perception://scan/{scan_id}/screenshot.png` |
| `agent_summary` | ✅ Included in observe responses (full + summary_only) |
| Progressive budget | ✅ `detail: "summary_only"` or `detail: "full"` |
| Publish | ✅ README updated with `pip install` + `uvx --from frontend-perception-engine frontend-perception-mcp`; no MCP API keys required |

---

## 6. Contract layers (behavior, not API reference)

| Layer | Programs the agent by… |
|-------|-------------------------|
| **`AGENT_GUIDE.md`** | Step-by-step playbooks per frontend task |
| **MCP `instructions`** | Universal loop + “read playbooks first” |
| **Tool descriptions** | When in the playbook to call each tool |
| **JSON schemas** | Exact parameter shapes only |
| **Tool responses** | Structured facts (`agent_summary`, `verified`, `reasons`) — never “you should next…” |

The MCP **never** returns planning hints. Playbooks + tool wiring teach the brain.

---

## 7. Interaction contract (summary)

### Standard envelope

Every tool returns:

```json
{
  "contract_version": "1.0",
  "tool": "perception_observe",
  "ok": true,
  "session_id": "sess_abc",
  "run_id": "run_001",
  "scan_id": "scan_042",
  "url": "http://localhost:5173/...",
  "error": null,
  "degraded": [],
  "data": {}
}
```

### Agent orchestration loop (agent only — MCP never runs this)

```text
1. PLAN    → agent picks route / component / flow checkpoint
2. OPEN    → perception_health (if needed)
             → perception_navigate_and_observe (save scan_id)
3. ANALYZE → read agent_summary.blocking; check auth_gate
4. ACT     → edit repo code OR perception_execute_script / execute_actions
5. VERIFY  → perception_verify(criteria); optional perception_diff
6. DECIDE  → pass → next step; fail → back to 3/4
```

### Global agent rules (teach the brain)

1. Always **observe** affected routes after UI changes.
2. Never trust clicks — always **verify** after execute.
3. Read **blocking** issues before advisory.
4. **Screenshot** on verify failure (`include_screenshot: true`).
5. **Stop** if `perception_auth_gate` → `requires_human: true`.
6. **probe_form** before filling forms; invalid submit first, then valid.
7. **state_save/restore** for multi-step auth flows.
8. **flow_describe** + per-checkpoint verify for multi-step flows.

Full playbooks: [`AGENT_GUIDE.md`](AGENT_GUIDE.md).

---

## 8. Repository layout (target)

```text
src/navigation/
├── perception/          # existing engine (unchanged responsibilities)
├── codeGraph/           # optional CRG hints
├── mcp/                 # NEW — server, session, registry, handlers
│   ├── server.py
│   ├── session_store.py
│   ├── scan_registry.py
│   ├── envelope.py
│   └── tools/
│       ├── lifecycle.py
│       ├── observe.py
│       ├── execute.py
│       ├── verify.py
│       └── probes.py
└── browser_use/         # optional autonomous path (not MCP default)

├── MCP_PLAN.md          # this file
└── AGENT_GUIDE.md       # host agent behavior program (primary contract)

src/run_mcp_contract_tests.py
```

---

## 9. Success criteria (product)

| # | Criterion |
|---|-----------|
| 1 | MCP runs with **zero** LLM/API keys |
| 2 | Host agent completes observe → execute → verify loop on sandbox |
| 3 | All engine features available as typed tools (M2) |
| 4 | New agent reads `AGENT_GUIDE.md` once and follows playbooks without MCP planning hints |
| 5 | `run_all_phases.py` + `run_mcp_contract_tests.py` green in CI |
| 6 | Free distribution: `uvx --from frontend-perception-engine frontend-perception-mcp` + Cursor config |

---

## 10. Implementation order (strict)

```text
M1  SessionStore + Envelope + 5 core tools + manual Cursor smoke test  ✅
M2  Remaining tools + perception_diff + contract tests  ✅
M3  Wire AGENT_GUIDE into MCP instructions + tool descriptions + Cursor rule  ✅
M4  Resources, agent_summary, packaging, README update  ✅
```

Do **not** start Tier C dev insights, autonomous agent improvements, or CRG fusion until M1–M3 ship — unless a tool explicitly needs them.

---

## 11. Relationship to other docs

| Doc | Role |
|-----|------|
| **MCP_PLAN.md** (this file) | North star — what we build and why |
| **AGENT_GUIDE.md** | **Primary contract** — programs agent behavior via playbooks |
| **STAGES.md** | Engine phases 1–4 (complete) |
| **What_to_build.md** | Problem → solution matrix |
| **README.md** | Install + quickstart (update at M4) |

---

## 12. One-sentence aim (constant)

**Program the coding agent to be the brain; give it a deterministic MCP runtime — and teach it how to work through playbooks, not API docs.**
