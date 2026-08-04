# Agent-Brain Coordination — Experiment Plan (EXP-025)

> **For agentic workers:** This is a **behavior experiment**, not an MCP complexity plan. Do not add owed gates.

**Goal:** Prove that teaching the agent to decide from the coordination scoreboard beats adding more MCP machinery.

**Architecture:** MCP stays Perfect Layer facts (gate, portfolio, backlog, cards). Treatment = agent rule §2b + `perception://agent-coordination`. Control = prior singular-next binding only.

**Tech Stack:** Cursor rules, methodology resources, live redesign sessions, scorecard MD.

---

### Task 1: Spec + experiment folder

- [x] Spec: `docs/superpowers/specs/2026-07-18-agent-brain-coordination-design.md`
- [x] EXP-025 README + scorecard
- [x] INDEX row

### Task 2: Agent contract (treatment)

- [x] `.cursor/rules/frontend-perception-mcp.mdc` §2b
- [x] `src/navigation/cli/data/frontend_mcp_agent_rule.md` §2b
- [x] `perception://agent-coordination` methodology resource

### Task 3: Live A/B (human + agent)

- [x] Arm A: historical PrimeStay / flow-craft feedback report as control
- [x] Arm B: Maze redesign-intent session with §2b; `scorecard.md` filled
- [x] Verdict in EXP-025 README — **B wins**

### Task 4: Freeze

- [x] B won: freeze — no new portfolio claim gates; keep §2b + agent-coordination resource
- [ ] If hosts still tunnel without §2b later: only consider card `owed[]` hint (still no claim gate)
