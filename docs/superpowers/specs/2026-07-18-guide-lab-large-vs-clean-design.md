# Guide Lab — Large Docs vs Clean Guides (EXP-026)

**Date:** 2026-07-18  
**Status:** Approved to implement  
**Constraint:** Runs only on **separated dev MCP** `frontend-mcp-guide-lab` — does **not** modify production `frontend-mcp` / `user-frontend-mcp`.

---

## 1. Hypothesis

Agents skip tools when guidance is long and singular (`gate.next` dominates).  
**Shorter scenario-first guides** produce better owed-plan decisions than the current large methodology stack — without adding MCP gates.

## 2. Isolation (frozen)

| Surface | Touched? |
|---------|----------|
| Production `frontend-mcp` / `methodology_resources.py` / PyPI preview | **No** |
| Production `.cursor/rules/frontend-perception-mcp.mdc` | **No** (experiment copies only) |
| New package `frontend-mcp-guide-lab` | **Yes** — resources + quiz CLI |
| `evals/guide_lab/` | **Yes** — arms, scenarios, scorecard |

## 3. Arms

| Arm | Prompt pack |
|-----|-------------|
| **A — Large** | Snapshot of current long agent rule + methodology excerpts (noisy, multi-URI) |
| **B — Clean** | New short guides only (~1 screen each, scenario tables + hard fails) |

## 4. Isolated quizzes (no browser)

Each YAML case: ask, task class, unpaid, gate, backlog.top → gold owed / first_family / must_not.

**Policy runner (deterministic, offline):**

- Arm A policy: tunnel — pick only family of `gate.next` / recommended singular pitch  
- Arm B policy: clean-guide algorithm — owed ≤3 from unpaid ∩ class; first = top if in owed  

This measures whether clean guides *encode* better decisions. Optional later: LLM mode with same YAML.

## 5. Success

B accuracy ≥ A on gold; especially tunnel / mockup / hotfix classes.  
If B wins → promote clean guides into production methodology in a **separate** follow-up (not this package).

## 6. Non-goals

New coordination gates, live browser redesigns, publishing guide-lab to PyPI as default MCP.
