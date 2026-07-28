# Experiment: agent-face-simple

**Branch:** `exp/agent-face-simple`  
**Parent research:** `docs/research/agent-facing-contract-simplification-2026-07-28.md`  
**Status:** **CUT OVER** on this branch (card-first face is the product contract).

## What shipped

| Artifact | Change |
|----------|--------|
| `.cursor/rules/frontend-perception-mcp.mdc` | Short spine + `next_args` |
| `src/navigation/cli/data/frontend_mcp_agent_rule.md` | Aligned to card |
| `src/navigation/mcp/instructions.py` | Short MCP preamble |
| `agent_summary.card` | `class/depth/next/next_args/owed/gate/claim_ok/claim_extra/finish/resource` |
| `perception://spine/{greenfield,redesign,feature,hotfix,forms}` | 5 short resources |
| `perception://getting-started` | Card-first + spines |
| `AGENT_GUIDE.md` | Points at card; long guide = L3 archive |

**Not rewritten:** coordination PSM/gate/portfolio brain, tool set, inspiration engines.

## Evidence (cutover gate)

| Check | Result |
|-------|--------|
| `tests/test_coordinator_card.py` | 17 passed |
| `tests/test_mcp_bootstrap_contract.py` | card-first phrases |
| No-guide E2E (`scripts/eval_agent_face_no_guide_e2e.py`) | BOARD PASS 4/4, follow=1.00 |
| Hang / wrong-next weaknesses | Fixed (forms spine, snapshot `then`, verify ladder) |

See `docs/research/agent-face-cutover-ab-2026-07-28.md`.

## Merge note

Merge this branch when ready; hosts must **reload MCP** after pull so instructions/resources refresh.
