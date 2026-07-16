# Preview: v1.2.0-dev — Decision-Centric Engineering Strategy

**Status:** Experimental preview — not stable. Do not merge validation feedback into `main` until a week of real-project testing passes.

**Branch:** `coordination-sandbox`  
**Current preview:** `1.2.0.dev3`

## What changed (behavioral)

### Engineering Strategy + Spec loop
Every frontend task surfaces `agent_summary.engineering_strategy` on health / session_start / observe. Host should read unresolved decisions and influence before coding.

### Image-first Inspiration + browser restore (`dev3`)
- Inspiration collect: progressive queries → CDN/preview images → ephemeral blobs; stop at 3–5 refs
- Browser screenshot only as explicit fallback
- Park/restore app URL so gallery tools do not leave Chromium on external sites
- Coordinator recommends `suggested_queries` when inspiration has ROI

### Cursor rules (host methodology)
Canonical rule file (copy into consumer projects):

`docs/cursor-rules/frontend-mcp.mdc` → `.cursor/rules/frontend-mcp.mdc` (`alwaysApply: true`)

Forces decision-before-code when the prompt is frontend-related; skips MCP for unrelated backend/infra work.

## Install preview (PyPI)

**Published:**

- https://pypi.org/project/frontend-perception-engine/1.2.0.dev3/
- https://pypi.org/project/frontend-mcp/1.2.0.dev3/

```bash
pip install --upgrade "frontend-mcp==1.2.0.dev3" "frontend-perception-engine==1.2.0.dev3"
```

Or from repo:

```powershell
.\scripts\install_preview_dev.ps1
```

**Windows file lock:** If `frontend-mcp.exe` is in use (Cursor MCP running), quit Cursor first, then install, then restart.

Verify:

```bash
python -c "import importlib.metadata as m; print(m.version('frontend-mcp'), m.version('frontend-perception-engine'))"
```

Expected: `1.2.0.dev3` for both.

## Install Cursor rules (consumer apps)

```powershell
# From this repo, or download the raw file from GitHub
New-Item -ItemType Directory -Force -Path .cursor\rules | Out-Null
Copy-Item path\to\frontend-perception-engine\docs\cursor-rules\frontend-mcp.mdc .cursor\rules\frontend-mcp.mdc
```

Or paste the same content into root `AGENTS.md` (without YAML frontmatter) for Codex / Claude Code.

## Cursor MCP config

Point at the installed executable (not dev checkout `PYTHONPATH`):

```json
{
  "mcpServers": {
    "frontend-mcp": {
      "command": "C:/Users/<you>/Miniconda3/Scripts/frontend-mcp.exe",
      "env": {
        "PYTHONPATH": ""
      }
    }
  }
}
```

Restart Cursor after install.

## Bootstrap with intent

```text
perception_health({ url: "http://localhost:5173", intent: "Build a SaaS dashboard" })
perception_session_start({ base_url: "...", intent: "Build a SaaS dashboard", repo_root: "..." })
→ Read agent_summary.engineering_strategy before coding
```

## What to test (influence, not correctness)

Run **real projects** — not synthetic unit tests:

| Project type | Expect influence |
|--------------|------------------|
| SaaS dashboard, landing, CRM, portfolio | `structural` — design/hierarchy before code |
| Marketing page, redesign | `structural` — inspiration when appropriate |
| Design system setup | `structural` / `architecture` |
| Feature addition (existing app) | `balanced` |
| Bug fix, responsive fix | `minimal` — observe/fix/verify |
| Production hotfix | `minimal` / `maintenance` |

Compare against:

1. Cursor without MCP
2. Stable MCP (`1.1.7`)
3. Preview MCP (`1.2.0.dev3`)

### Questions (success = influence)

- Did the agent classify the prompt as frontend and follow the rules?
- Did it stop and read strategy before coding?
- Did inspiration stay image-first (≤3–5 refs) without polluting the browser session?
- Did the final UI actually improve?

## Sandbox (synthetic tuning)

```bash
python -m coordination_sandbox.run --scenarios coordination_sandbox/scenarios/default.yaml
```

## Promotion path

1. Run preview on multiple real projects for ~1 week
2. Tune policies in sandbox if needed (stay on `coordination-sandbox`)
3. When influence consistently improves outcomes → merge to `main`
4. Publish stable **`1.2.0`**

Do **not** publish preview as the default unpinned `pip install frontend-mcp` target — pin the version.
