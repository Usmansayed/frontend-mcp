# Install & setup — Frontend MCP

One package. One install command:

```bash
pip install frontend-mcp
```

Upgrade later with:

```bash
pip install -U frontend-mcp
```

Optional Chromium for Browser Use:

```bash
frontend-mcp-install --with-browser
# or
uvx playwright install chromium
```

Then wire the MCP into your coding agent (below) and optionally install host rules:

```bash
cd /path/to/your-app
frontend-mcp install rules --tool cursor   # or: claude | opencode | codex
```

Rules are **optional**. The MCP server already ships baked-in instructions. Rules make Cursor / Claude / Codex / OpenCode follow the evidence loop more reliably.

---

## Quick check

```bash
frontend-mcp --help
python -c "import navigation; print('ok')"
```

Smoke after the agent reloads MCP:

1. `perception_health({url, intent})`
2. `perception_session_start({base_url, intent})`
3. Read `agent_summary.card`

---

## Cursor

### 1. Install package

```bash
pip install frontend-mcp
```

### 2. MCP config

Edit **Cursor Settings → MCP** or `~/.cursor/mcp.json` (Windows: `%USERPROFILE%\.cursor\mcp.json`):

```json
{
  "mcpServers": {
    "frontend-mcp": {
      "command": "frontend-mcp",
      "args": []
    }
  }
}
```

Prefer always-latest without a global pip install:

```json
{
  "mcpServers": {
    "frontend-mcp": {
      "command": "uvx",
      "args": ["--from", "frontend-mcp", "frontend-mcp"]
    }
  }
}
```

### 3. Rules (recommended)

In your app repo:

```bash
frontend-mcp install rules --tool cursor
```

Writes `.cursor/rules/frontend-perception-mcp.mdc`.

### 4. Reload

Restart Cursor / reload MCP. Confirm tools appear under the `frontend-mcp` server.

---

## Claude Code

### 1. Install package

```bash
pip install frontend-mcp
```

### 2. MCP config (project)

Create `.mcp.json` in the project root (safe to commit if it has no secrets):

```json
{
  "mcpServers": {
    "frontend-mcp": {
      "type": "stdio",
      "command": "frontend-mcp",
      "args": []
    }
  }
}
```

Or add via CLI:

```bash
claude mcp add --transport stdio frontend-mcp -- frontend-mcp
```

User-scoped (all projects): `claude mcp add --scope user …` (writes `~/.claude.json`).

### 3. Rules (recommended)

```bash
frontend-mcp install rules --tool claude
```

Writes `.claude/rules/frontend-perception-mcp.md`.

### 4. Verify

```bash
claude mcp list
```

---

## OpenAI Codex

### 1. Install package

```bash
pip install frontend-mcp
```

### 2. MCP config

Edit `~/.codex/config.toml` (global) or `.codex/config.toml` (project, trusted):

```toml
[mcp_servers.frontend-mcp]
command = "frontend-mcp"
args = []
startup_timeout_sec = 20
tool_timeout_sec = 120
```

With `uvx`:

```toml
[mcp_servers.frontend-mcp]
command = "uvx"
args = ["--from", "frontend-mcp", "frontend-mcp"]
startup_timeout_sec = 30
tool_timeout_sec = 120
```

### 3. Rules (recommended)

```bash
frontend-mcp install rules --tool codex
```

Merges Frontend MCP guidance into `AGENTS.md`.

### 4. Verify

In the Codex TUI: `/mcp`, or `codex mcp list`.

---

## OpenCode

### 1. Install package

```bash
pip install frontend-mcp
```

### 2. MCP config

Add to `opencode.json` / `opencode.jsonc` (project or global OpenCode config):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "frontend-mcp": {
      "type": "local",
      "command": ["frontend-mcp"],
      "enabled": true
    }
  }
}
```

With `uvx`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "frontend-mcp": {
      "type": "local",
      "command": ["uvx", "--from", "frontend-mcp", "frontend-mcp"],
      "enabled": true
    }
  }
}
```

### 3. Rules (recommended)

```bash
frontend-mcp install rules --tool opencode
```

Merges into `AGENTS.md`.

### 4. Verify

```bash
opencode mcp list
```

---

## Recommended host loop (all agents)

```text
perception_health({url, intent})
  → fix data.doctor if critical
→ perception_session_start({base_url, intent})
→ read agent_summary.card (orders / owed / next)
→ prefer perception_step({session_id})
→ LOOK inspiration → implement ~80–90% copy → consistency → verify
→ claim only if claim_ok
```

Browser tools: **one at a time** per `session_id`. HTTP intel families may run in parallel when `card.can_parallel` says so.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pip install frontend-mcp` gets an old 1.1.x | `pip install -U frontend-mcp` |
| Agent has no tools | Reload MCP; confirm `frontend-mcp` is on PATH (`where frontend-mcp` / `which frontend-mcp`) |
| `uvx` preferred | Use the `uvx --from frontend-mcp frontend-mcp` config variants above |
| Editable + PyPI mixed | Uninstall both, then only `pip install frontend-mcp` (do not mix with `pip install -e .`) |
| Browser missing | `frontend-mcp-install --with-browser` |
| Version skew after upgrade | Restart the agent / MCP process |

Legacy package name still works (pulls the same `frontend-mcp`):

```bash
pip install frontend-perception-engine
```

Prefer **`frontend-mcp`**.
