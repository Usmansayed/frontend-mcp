# Preview: v1.2.0-dev — Decision-Centric Engineering Strategy

**Status:** Experimental preview — not stable. Do not merge validation feedback into `main` until a week of real-project testing passes.

**Branch:** `coordination-sandbox`

## What changed (behavioral)

Every frontend task now surfaces `agent_summary.engineering_strategy` on:

- `perception_health` (optional `intent`)
- `perception_session_start` (**pass `intent`** describing the task)
- All coordinator-enriched tool responses (observe, verify, etc.)

The host should read **unresolved decisions and influence level** before planning implementation — not tool lists first.

## Install preview (PyPI)

**Published:**

- https://pypi.org/project/frontend-perception-engine/1.2.0.dev2/
- https://pypi.org/project/frontend-mcp/1.2.0.dev2/

```bash
pip install --upgrade "frontend-mcp==1.2.0.dev2" "frontend-perception-engine==1.2.0.dev2"
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

Expected: `1.2.0.dev2` for both.

## Install preview (local wheel)

From repo root on `coordination-sandbox`:

```powershell
python -m build
pip install --force-reinstall dist/frontend_perception_engine-1.2.0.dev2-*.whl
cd packages/frontend-mcp
python -m build
pip install --force-reinstall dist/frontend_mcp-1.2.0.dev2-*.whl
```

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
3. Preview MCP (`1.2.0.dev2`)

### Questions (success = influence)

- Did the agent stop and read strategy before coding?
- Did it establish design direction on greenfield work?
- Did it spend effort on layout/hierarchy vs pixel tweaks?
- Did it use inspiration when appropriate (and skip it on hotfixes)?
- Was the workflow still fast?
- Did the final UI actually improve?

## Sandbox (synthetic tuning)

Before or alongside real-project testing:

```bash
python -m coordination_sandbox.run --scenarios coordination_sandbox/scenarios/default.yaml
```

Reports go to `coordination_sandbox/output/`.

## Promotion path

1. Run preview on multiple real projects for ~1 week
2. Tune policies in sandbox if needed (stay on `coordination-sandbox`)
3. When influence consistently improves outcomes → merge to `main`
4. Publish stable **`1.2.0`** (drop `.dev1`)

Do **not** publish `1.2.0.dev2` as the default `pip install frontend-mcp` target — it requires an explicit version pin.
