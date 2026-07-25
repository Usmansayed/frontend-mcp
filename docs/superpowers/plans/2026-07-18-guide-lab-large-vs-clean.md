# Guide Lab Large vs Clean — Plan (EXP-026)

> **Isolated:** `frontend-mcp-guide-lab` only. Do not edit production MCP.

**Goal:** Prove clean scenario guides beat large docs on isolated decision quizzes.

**Architecture:** Arms + YAML quizzes + policy runner under `evals/guide_lab/`; thin MCP server package serves `guide-lab://` resources only.

**Tech Stack:** Python, PyYAML, mcp (resources-only server), pytest.

---

### Task 1: Scaffold

- [x] Spec + plan
- [x] `evals/guide_lab/` + `packages/frontend-mcp-guide-lab/`
- [x] `src/navigation/guide_lab/` runner + policies

### Task 2: Clean guides (Arm B)

- [x] scoreboard, greenfield, redesign, feature, hotfix-polish, hard-fails

### Task 3: Arm A snapshot

- [x] Copy large excerpts (read-only snapshot)

### Task 4: Scenarios + run

- [x] 24 quiz YAML with gold
- [x] Score A vs B — **B 24/24, A 2/24**; scorecard + EXP INDEX
