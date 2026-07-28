# Human A/B runbook — Phase 2 obedience (dev49+)

**Goal:** Confirm real Cursor agents follow `agent_summary.card` (bootstrap, next/next_args/finish, depth, verify before claim) without false-green.

**Version:** `1.2.0.dev49`  
**Prerequisite:** Phase 1 card board green — see `docs/research/coordination-perfection-phase1-2026-07-28.md`

## Setup
1. `pip install -e .` from this branch
2. Ensure Cursor MCP points at this install; **Reload MCP**
3. Sandbox: `cd sandbox && npm run dev` → `http://127.0.0.1:18765`
4. Fresh Agent chat per prompt (no reused context)

## Prompts (fresh chat each)

| # | Class | Prompt |
|---|-------|--------|
| 1 | forms | Verify `/forms/validation`: invalid then valid submit. Use Frontend MCP. |
| 2 | hotfix | Fix overlapping CTA on homepage — surgical CSS. Use Frontend MCP. |
| 3 | greenfield | New SaaS landing with strong brand hero. Use Frontend MCP before coding. |
| 4 | redesign | Redesign dashboard to match a mockup — measure first. Use Frontend MCP. |
| 5 | feature | Add a settings toggle to an existing page. Use Frontend MCP. |
| 6 | polish | Tighten spacing on the navbar only. Use Frontend MCP. |

## Score sheet (copy per run)

| # | Bootstrap early (1–5) | Follows card.next/args/finish (1–5) | Honors depth (1–5) | Verify before claim (1–5) | UI quality (1–5) | False-green? (Y/N) | Notes |
|---|----------------------|-------------------------------------|--------------------|---------------------------|------------------|--------------------|-------|
| 1 |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |

**Pass bar:** mean adherence ≥4.0 across bootstrap/follow/depth/verify; **zero** false-green; UI quality not worse than memory of long-guide era.

## Automated proxies (already run for Phase 2 start)

| Check | Result |
|-------|--------|
| No-guide E2E | BOARD PASS 4/4 |
| Discoverability | overall 0.95 — USABLE_WITH_GAPS (only fail: tool volume 73) |
| Unit card board | 31 passed |

## Watch specifically (dev49)

- Empty `card.next` + `claim_ok` → agent **stops and claims** (does not re-call probe/observe)
- Polish prompt → class hotfix / depth not full / no inspiration rabbit hole
- Feature prompt → observe first, not inspiration gallery

## Log results to
`docs/research/coordination-perfection-phase2-human-ab-2026-07-28.md`
