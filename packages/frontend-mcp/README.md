# frontend-mcp

PyPI alias for [frontend-perception-engine](https://pypi.org/project/frontend-perception-engine/).

Deterministic browser runtime + fast code resolvers for AI coding agents.

## Install

```bash
pip install frontend-mcp
frontend-mcp-install    # writes Cursor mcp.json
frontend-mcp
```

Or:

```bash
uvx --from frontend-mcp frontend-mcp-install
uvx --from frontend-mcp frontend-mcp
```

## Agent quick start

1. Read **`perception://agent-guide`** at session start
2. `perception_health` → `perception_session_start`
3. `perception_navigate_and_observe` → save `scan_id`
4. Code ↔ UI: **`perception://resolver-guide`** → `perception_resolve_route` (not `perception_code_context`)
5. Edit files → `perception_verify` (never skip)

## Key MCP resources

| URI | Use |
|-----|-----|
| `perception://agent-guide` | Main playbooks |
| `perception://resolver-guide` | `perception_resolve_*` tools |
| `perception://seo-guide` | `perception_seo_audit_start` + poll |

## Local development

Point Cursor at your checkout:

```json
{
  "mcpServers": {
    "frontend-mcp": {
      "command": "python",
      "args": ["-m", "navigation.mcp"],
      "env": {
        "PYTHONPATH": "/path/to/frontend-perception-engine/src",
        "FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT": "/path/to/frontend-perception-engine/sandbox"
      }
    }
  }
}
```

Restart MCP after changes. Run smoke: `python scripts/phase3_mcp_smoke.py`
