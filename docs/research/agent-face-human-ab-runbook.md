# Human A/B runbook — agent-face cutover

**Goal:** Confirm card-first face beats long-guide control in real Cursor chats before tagging a non-dev release.

## Setup
1. Install: `pip install -e .` from this branch (`1.2.0.dev48+`)
2. Ensure `~/.cursor/mcp.json` runs this install (`PYTHONPATH=.../src` or editable)
3. **Reload MCP** in Cursor
4. Sandbox: `cd sandbox && npm run dev` → `http://127.0.0.1:18765`

## Prompts (fresh chat each)

| # | Class | Prompt |
|---|-------|--------|
| 1 | forms | Verify `/forms/validation`: invalid then valid submit. Use Frontend MCP. |
| 2 | hotfix | Fix overlapping CTA on homepage — surgical CSS. Use Frontend MCP. |
| 3 | greenfield | New SaaS landing with strong brand hero. Use Frontend MCP before coding. |
| 4 | redesign | Redesign dashboard to match a mockup — measure first. Use Frontend MCP. |
| 5 | feature | Add a settings toggle to an existing page. Use Frontend MCP. |
| 6 | polish | Tighten spacing on the navbar only. Use Frontend MCP. |

## Score (1–5 each)
- Bootstrap early (health→session before big UI)?
- Follows `card.next` / `next_args` / `finish`?
- Honors `depth` (no invented ship on hotfix)?
- Verify before claim (`data.verified` + `claim_ok`)?
- UI quality 1–5
- False-green claim? (Y/N)

## Pass bar
Simple face wins on adherence + false-green without UI quality loss vs memory of old long-guide behavior.

## Automated proxy already green
`scripts/eval_agent_face_no_guide_e2e.py` BOARD PASS 4/4 — see `docs/research/agent-face-cutover-ab-2026-07-28.md`.
