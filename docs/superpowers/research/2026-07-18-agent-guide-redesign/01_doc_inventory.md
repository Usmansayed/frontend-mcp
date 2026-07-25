# 01 — Agent-Facing Doc Inventory

**Sources:** repo rules, CLI agent rule, methodology resources, Guide Lab arms, specialist guides.

## Layer A — Always-on host rules (highest attention)

| Path | ~Words | Role |
|------|--------|------|
| `.cursor/rules/frontend-perception-mcp.mdc` | ~1.5k | Always-applied Cursor rule: bootstrap, fields, §2b brain, situations, Done ladder, never |
| `src/navigation/cli/data/frontend_mcp_agent_rule.md` | ~1.5k | Installable copy of the same rule for non-Cursor hosts |

**Observation:** This file is already a “large guide” that also embeds §2b. Agents still tunnel because **singular fields** (`next_required_capability`, `recommended_evidence`) are easier to obey than tables.

## Layer B — Progressive methodology (`perception://`)

Served from `src/navigation/mcp/methodology_resources.py` (production MCP).

| URI | Title | Role |
|-----|-------|------|
| `perception://getting-started` | Getting Started | Bootstrap order; stop-coding-if-skipped |
| `perception://frontend-methodology` | Frontend Methodology | Generic loop when no specific workflow |
| `perception://design-workflow` | Greenfield Design | New product/page foundation path |
| `perception://redesign-workflow` | Redesign | Snapshot / SpecDiff path |
| `perception://bugfix-workflow` | Bugfix | Observe → fix → verify |
| `perception://engineering-strategy` | Engineering Strategy | How to read strategy/card/portfolio |
| `perception://agent-coordination` | Agent-Brain Coordination | §2b short form (workspace; may be missing on older installs) |
| `perception://decision-ledger` | Decision Ledger | Evidence lifecycle |
| `perception://ship-council` | Ship Council | Post-verify ship gate |
| `perception://verification-guide` | Verification Guide | `data.verified`, sections, Spec gate |
| `perception://browser-lifecycle` | Browser Lifecycle | Single Chromium owner |

**Also referenced in MCP instructions (not all in METHODOLOGY_RESOURCES):**  
`agent-guide`, `resolver-guide`, `seo-guide`, `inspiration-guide`, `resource-guide`, `figma-guide`.

## Layer C — Specialist long docs (deep reference)

| Area | Example path | Role |
|------|--------------|------|
| Inspiration | `src/navigation/inspiration_intelligence/docs/INSPIRATION_AGENT_GUIDE.md` | Gallery providers, FAST mode, collect behavior |
| Inspiration | `.../ARCHITECTURE.md` | Internals |
| Resources / SEO / Figma | various `*/docs/` | Specialist |

**Observation:** Deep docs are valuable for tool authors and rare edge cases. They are **poor primary prompts** for turn-by-turn decisions.

## Layer D — Guide Lab experiment (dev only)

| Path | Role |
|------|------|
| `evals/guide_lab/arms/arm_a_large/` | Snapshot of large rule + methodology bundle |
| `evals/guide_lab/arms/arm_b_clean/` | First-draft short guides (to be redesigned after this research) |
| `evals/guide_lab/scenarios/` | Gold decision quizzes |
| `packages/frontend-mcp-guide-lab/` | Separate MCP; not production |

## Attention budget (research conclusion)

Agents reliably consume:

1. Cursor always-on rule (partially)  
2. Whatever `recommended_resource` points to (sometimes)  
3. `gate.next` / `host_action` one-liners (almost always)

Agents rarely consume:

- Full methodology bundle  
- Multi-URI progressive reads after the first  
- Portfolio unpaid as a binding set (unless §2b is salient and short)

**Implication for guide design:** One **short primary contract** + thin scenario cards; long docs stay secondary (`read when recommended_resource says so`).
