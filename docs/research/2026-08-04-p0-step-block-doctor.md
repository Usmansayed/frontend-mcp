# P0 agent improvisations (`1.2.0.dev67`)

From the Aug 2026 agent experience report — three high-leverage fixes:

## 1. `perception_step` (Tier-0)
Executes `agent_summary.card.next` with `card.next_args` in one call.
- Prefer over inventing nearby tools.
- `dry_run=true` resolves only.
- Nested `perception_step` refused.

## 2. Hard `implement_blocked`
While `card.implement_blocked`, MCP **refuses**:
- `perception_execute_script`
- `perception_execute_actions`
- `perception_integrate_component`
- `perception_design_review(mode=ship)`

Returns a short envelope with `owed_top` + `next` / `next_args` — not an essay.
Observe / verify / inspiration / resources stay allowed.

## 3. Health doctor
`perception_health` → `data.doctor`:
- checks: app_url, browser_use, chromium, node, repo_root, version_skew
- `fix_commands` copy-paste list
- `primary_browser: perception` (avoid dual-driving Cursor/Playwright MCP)

## Host loop
```
perception_health → read doctor.fix_commands
→ session_start({intent})
→ loop: perception_step({session_id}) until claim_ok
```
