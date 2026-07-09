# Grounded Docs MCP (fork)

Upstream: [arabold/docs-mcp-server](https://github.com/arabold/docs-mcp-server) (Grounded Docs)

This directory tracks our fork of Grounded Docs MCP. **Do not add Frontend Perception logic here** — all custom integration lives in:

`src/navigation/framework_intelligence/providers/grounded_docs/`

## Pin

| Field | Value |
|-------|--------|
| Upstream repo | `https://github.com/arabold/docs-mcp-server` |
| npm package | `@arabold/docs-mcp-server` |
| Pinned version | `2.4.2` (see `client.py` `PINNED_VERSION`) |

## Initialize fork (optional local checkout)

```bash
git submodule add https://github.com/Usmansayed/grounded-docs-mcp.git vendor/grounded-docs-mcp
# Or track upstream directly:
git submodule add https://github.com/arabold/docs-mcp-server.git vendor/grounded-docs-mcp
cd vendor/grounded-docs-mcp && npm ci && npm run build
```

## Runtime

By default the Python adapter invokes the pinned npm CLI via `npx`.

Override with environment variables:

| Variable | Purpose |
|----------|---------|
| `GROUNDED_DOCS_CLI` | Path to `docs-mcp-server` binary (built fork) |
| `GROUNDED_DOCS_STORE_PATH` | Shared SQLite store path for scrape/search |
| `GROUNDED_DOCS_SCRAPE_TIMEOUT_S` | On-demand scrape timeout (default 300) |

## Merging upstream

1. `cd vendor/grounded-docs-mcp && git fetch upstream && git merge upstream/main`
2. Bump `PINNED_VERSION` in `providers/grounded_docs/client.py` after release
3. Run contract tests — adapter layer unchanged unless CLI contract changes
