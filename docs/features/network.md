# Network subsystem

**Status:** ✅ shipped (v0.5)  
**Module:** `src/navigation/network/`  
**CDP domain:** `Network`

## Goals

| Capability | v0.2 | v0.5 (shipped) |
|------------|------|----------------|
| failed requests | ✅ dev_insights | ✅ full lifecycle |
| slow requests | ✅ threshold | ✅ configurable (default 1000ms) |
| request/response headers | ❌ | ✅ |
| bodies | ❌ | ✅ size-capped (64KB) |
| redirect chain | ❌ | ✅ |
| HAR export | ❌ | ✅ `perception://scan/{id}/network.har` |
| duplicate detection | heuristic | ✅ |
| API grouping | path prefix | ✅ + GraphQL op name |

## Architecture

```
CdpHub
  └─ NetworkCollector (enable Network, buffer events)
       └─ NetworkEntry (pydantic per requestId)
            └─ NetworkReport → agent_summary.network
```

## HAR

Generate HAR 1.2 from buffered entries on scan finalize. Cap body size (e.g. 64KB) to avoid memory blowups.

## Slow / duplicate heuristics

- **Slow:** duration > `slow_threshold_ms` (default 1000)
- **Duplicate:** same method + normalized URL within 2s window

## GraphQL

Parse POST body for `query` / `operationName` when `content-type` is JSON — best-effort, no AST dependency required for v1.

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_network_get` | Filtered session history (`failed_only`, `api_group`, `contains`, `include_bodies`) |
| `perception_network_clear` | Wipe ring buffer |

Observe includes `data.observation.network` and `data.agent_summary.network` with failures/slow/duplicates prioritized in reports.

## Reference study

BrowserTools `getXHRResponses` / `getNetworkLogs` — study response shape for agent ergonomics, implement via CDP `Network.getResponseBody`.

## Tests

- Mock server returning 404, 302 redirect, slow response
- HAR JSON schema validation (subset)

## Related

- [console.md](./console.md)
- [reports.md](./reports.md)
