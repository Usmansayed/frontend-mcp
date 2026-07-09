# Console subsystem

**Status:** ✅ shipped (v0.4)  
**Module:** `src/navigation/console/`  
**CDP domains:** `Log`, `Runtime`

## Goals

Full console capture for coding agents without Chrome extension:

| Capability | v0.2 | v0.4 (shipped) |
|------------|------|----------------|
| error/warn during observe | ✅ `dev_insights` | ✅ ring buffer |
| log/info/debug | partial | ✅ |
| stack traces | partial | ✅ |
| exceptions | ✅ | ✅ |
| session history | ❌ | ✅ per session |
| filter by level | ❌ | ✅ `perception_console_get` |
| wipe / snapshot export | ❌ | ✅ `perception_console_clear` |

## Architecture

```
CdpHub
  └─ ConsoleCollector (subscribe Log.entryAdded, Runtime.exceptionThrown)
       └─ ConsoleBuffer (ring, max N entries per session)
            └─ ConsoleReport (pydantic) → agent_summary.console
```

## Report shape (draft)

```json
{
  "console": {
    "total": 42,
    "by_level": {"error": 2, "warn": 5},
    "entries": [
      {
        "level": "error",
        "text": "...",
        "timestamp": "...",
        "url": "...",
        "line": 12,
        "stack": ["..."]
      }
    ],
    "blocking": ["Uncaught TypeError: ..."]
  }
}
```

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_console_get` | Filtered session history (`levels`, `contains`, `since_index`, `limit`) |
| `perception_console_clear` | Wipe ring buffer |

Observe / navigate-and-observe include `data.observation.console` and `data.agent_summary.console` automatically.

`references/browser-tools-mcp/browser-tools-server/` — how they aggregate console for MCP responses. **Do not** copy WebSocket transport.

## Tests

- pytest-httpserver page with `console.log` / thrown error
- Observe captures entries deterministically
- Filter API unit tests on buffer

## Related

- [network.md](./network.md) — often correlated with console errors
- [reports.md](./reports.md) — console section in full diagnosis
