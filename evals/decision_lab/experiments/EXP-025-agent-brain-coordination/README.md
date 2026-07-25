# EXP-025 — Agent-Brain Coordination (vs more MCP gates)

**Date:** 2026-07-18  
**Status:** complete — B wins (freeze agent-brain)  
**Track:** Coordination simplicity — agent as brain  

## Hypothesis

Keeping MCP coordination as a **clean facts scoreboard** and teaching the **agent** how to decide from `portfolio.unpaid` + gate + backlog.top reduces tool-family tunnel vision **better than** adding more owed gates / supersede rules in MCP.

## Method

| Arm | MCP | Agent policy |
|-----|-----|----------------|
| **A — Control** | Current Perfect Layer (unchanged) | Current rule: bind singular `next` / `recommended_evidence` |
| **B — Treatment** | Same MCP (no new gates) | Agent-brain contract: unpaid families bind; brain builds ≤3 owed plan |

**Do not** ship new coordination complexity for B during this experiment.

## Agent-brain contract (treatment)

See: `docs/superpowers/specs/2026-07-18-agent-brain-coordination-design.md`  
Installed into: `.cursor/rules/frontend-perception-mcp.mdc` + `frontend_mcp_agent_rule.md` (§2b)

Short form:

1. Read `episode_card` / strategy: **unpaid + gate + backlog.top**  
2. Build owed plan (≤3) from unpaid ∩ task class  
3. Call one tool from owed; re-read unpaid before locking UI  
4. Inspiration when owed: one progressive collect (3–5 refs) — stop when usable  
5. Never claim done while gate prohibits claim or structural unpaid lack skip/supersede  

## Live eval protocol

1. Fresh episode on a real UI app (not Maze-as-wrong-port).  
2. Prompt: professional landing redesign **or** mockup match.  
3. Log tool families called vs `portfolio.unpaid` after each strategy refresh.  
4. Fill `scorecard.md` in this folder.

## Scorecard

| ID | Check | A | B |
|----|-------|---|---|
| S1 | Paid inspiration **or** snapshot before large UI code when design_reference unpaid | FAIL | PASS |
| S2 | Paid component foundation when foundation unpaid (redesign) | PASS | PASS |
| S3 | Observe + verify with `data.verified=true` before claim | PASS | PASS |
| S4 | No tunnel: ≥2 families used when unpaid ≥2 structural | FAIL | PASS |
| S5 | No new MCP gate/code for treatment | N/A | PASS |
| S6 | False-green / soft verify avoided on visual claims | FAIL | PASS |

**Win:** B ≥ A on S1–S4/S6 with S5 PASS.  
**Fail:** B still tunnels → consider **one** card field `owed[]` only (still no new claim gates).

## Lab note

Decision Lab stays facts-only (fake envelopes). This experiment is **host-behavior** — live Cursor agent sessions, not baseline YAML.

## Verdict

**B wins.** Teaching the agent to decide from `portfolio.unpaid` + gate + backlog.top beats adding more MCP owed gates.

- Arm A (historical PrimeStay / flow-craft): inspiration once, foundation ok, but mockup skipped Design/snapshot; opacity false-green.
- Arm B (§2b on Maze): inspiration timeout → snapshot supersede; component; observe; hard section verify — multi-family, **zero** new coordination code.

**Freeze:** keep MCP as facts scoreboard; keep §2b / `perception://agent-coordination` as the behavior contract. Do **not** grow Perfect Layer claim gates for unpaid portfolio. Revisit card `owed[]` hint only if hosts still tunnel without the rule.

Details: [`scorecard.md`](./scorecard.md)
