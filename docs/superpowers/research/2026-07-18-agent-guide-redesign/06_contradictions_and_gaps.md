# 06 — Contradictions and Gaps

## C1 — Portfolio advisory vs rule binding

**MCP code:** portfolio note says advisory; backlog.top is ROI next.  
**Agent rule §2b:** unpaid binds.  
**Gap:** Installed MCP without updated rule still tunnels.  
**Guide fix:** State clearly: “MCP won’t block you for unpaid; **you** must. Skipping unpaid without reason is a process fail.”

## C2 — Singular next vs multi-family unpaid

**host_action** often says both: “Next: X” and “Portfolio unpaid: A, B, C.”  
Agents obey “Next.”  
**Guide fix:** Lead with unpaid; demote next to “pick among owed.”

## C3 — recommended_evidence vs gate.next conflict

Observed live: gate.next = inspiration, recommended_evidence = component_select (or verify).  
**Guide fix:** Neither wins alone; owed plan ∩ unpaid wins; prefer top only if in owed.

## C4 — Large rule already has §2b but still long

Always-on rule mixes bootstrap + fields + §2b + situations + ladder + never (~full essay).  
§2b competes with §2 singular fields table that still says “prefer recommended_evidence.”  
**Guide fix:** Split: **primary card** (scoreboard + classes) vs **appendix** (bootstrap detail).

## C5 — Agent classes vs code task_scope names

Guides say greenfield/polish; code says design_driven/surgical.  
**Guide fix:** Use agent classes; footnote mapping for advanced hosts.

## C6 — Inspiration timeout vs unpaid

Inspiration can fail/timeout; unpaid may still list inspiration; snapshot supersedes.  
**Guide fix:** Explicit “failed inspiration → pay snapshot or skip with reason.”

## C7 — Sticky design vs polish

Surgical tweak during sticky redesign episode may still require ship.  
Current short Guide Lab guides oversimplify “polish skips ship.”  
**Guide fix:** Exception box: sticky design_driven draft this episode → finish ladder.

## C8 — Forms family underdocumented in short guides

Code has `forms` / `guards` families; Arm B clean guides barely mention probes.  
**Guide fix:** Dedicated short card for forms/flows.

## C9 — Resolve family weakly in portfolio unpaid

Portfolio CAPABILITY_FAMILY includes resolve, but unpaid logic rarely adds resolve from unresolved decisions (more observe/component/verify).  
Agents underuse resolve.  
**Guide fix:** Feature/hotfix “owners unclear → resolve” even if not in unpaid.

## C10 — Guide Lab Arm B is draft, not researched design

First clean guides were written to win policy quizzes quickly.  
**This research pack exists to replace them with validated design.**

## C11 — `perception://agent-coordination` may be missing on older installs

Workspace has it; installed `.dev13` may not until republish.  
**Guide fix:** Keep scoreboard contract inside always-on short rule, not only methodology URI.

## C12 — `.mdc` vs CLI agent rule drift

`frontend_mcp_agent_rule.md` includes KPI / `uneven_kpi_columns` guidance that `.cursor/rules/frontend-perception-mcp.mdc` may omit.  
**Guide fix:** Single source of truth; generate both from one short pack.

## C13 — V1.1.5 eval loop fights §2b

`evals/V1.1.5_AGENT_EVALUATION.md` frames “every frontend task” as observe→verify and omits strategy/portfolio/inspiration.  
**Guide fix:** Primary contract must overwrite that mental model explicitly.

## C14 — Empty unpaid off design scope

Feature/hotfix may see `portfolio.unpaid = []` while class still owes observe/verify.  
**Guide fix:** “If unpaid empty, still run class min path.”

## C15 — Gate ladder vs evidence plan order

Code priority: sections → blocked → residue → ship → evidence plan (`engineering_strategy` host_action overrides).  
Agents may jump to ship/verify while snapshot unpaid.  
**Guide fix:** Mirror ladder in Done card; unpaid structural refs still bind before ship.

## C16 — Possible `design_system` vs `design_system_posture` id mismatch

Research flagged `STRUCTURAL_DECISIONS` may use `"design_system"` while decision id is `"design_system_posture"` — posture might not enter blocking set.  
**Guide fix:** Don’t rely on gate alone for DS posture; foundation unpaid still binds. (Validate in code before promote.)

## C17 — External flow-craft feedback not versioned in repo

Primary live failure narrative lives under Downloads, not `evals/`.  
**Guide fix:** Copy sanitized excerpts into `evals/` when promoting guides.
