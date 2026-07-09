# Framework Intelligence (v1)

**Status:** ✅ shipped (v1.0)  
**Module:** `src/navigation/framework_intelligence/`

## Goal

This module does **not** maintain framework knowledge. It only:

1. Detects the project stack from local files
2. Collects factual project metadata (framework, version, build tool, etc.)
3. Routes documentation requests to a **documentation provider**
4. Returns **normalized** documentation to the host agent

The rest of the MCP never depends on Grounded Docs (or any provider) directly.

## Pipeline

```text
Project (repo_root)
    ↓
Framework Detector (no framework how-to knowledge)
    ↓
Project Metadata
    ↓
Documentation Provider (Grounded Docs today)
    ↓ adapter layer (registry, query builder, normalize)
Normalized Response
    ↓
Agent
```

## Framework Detector

Reads primarily from:

- `package.json`
- lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb`)
- config files (`vite.config.*`, `next.config.*`, `tsconfig.json`, etc.)
- folder structure (`src/`, `app/`, `pages/`, etc.)

Detects:

| Signal | Examples |
|--------|----------|
| Framework | React, Next.js, Vue, Angular, Svelte, Astro, Nuxt, Remix |
| Version | From dependency semver (major.minor) |
| Primary package | npm dependency name (e.g. `react`, `next`) — factual, not provider-specific |
| Build tool | Vite, Webpack, Rsbuild, Next.js bundler |
| Package manager | npm, pnpm, yarn, bun |
| Language | TypeScript vs JavaScript |
| Monorepo | workspaces, `pnpm-workspace.yaml`, `lerna.json`, `packages/` |
| Rendering | CSR, SSR/SSG hints when detectable |
| Router mode | Next.js App Router vs Pages Router |

Framework-specific doc routing (library names, scrape URLs) lives only in the **adapter** (`providers/grounded_docs/registry.py`), not in the detector.

## Grounded Docs integration

Upstream: [arabold/docs-mcp-server](https://github.com/arabold/docs-mcp-server) (pinned `@2.4.2`). Fork tracking: `vendor/grounded-docs-mcp/README.md`.

| Layer | Path | Responsibility |
|-------|------|----------------|
| Protocol | `providers/documentation.py` | `DocumentationProvider` interface |
| CLI client | `providers/grounded_docs/client.py` | Thin wrapper around upstream binary |
| Adapter | `providers/grounded_docs/adapter.py` | On-demand scrape + search orchestration |
| Registry | `providers/grounded_docs/registry.py` | npm package → library + scrape URL |
| Query builder | `providers/grounded_docs/query_builder.py` | Metadata-enriched search queries |
| Normalize | `providers/grounded_docs/normalize.py` | CLI JSON → `DocumentationResult` |

Flow:

1. Build a version-aware query from metadata + topic
2. `search <library> <query> --version X` via pinned CLI
3. If library not indexed → `scrape <library> <url>` on demand, then retry search
4. Normalize to `DocumentationResult` / `FrameworkKnowledgeResponse`

**Requirements:** Node.js 22+ with `npx` available.

| Env var | Purpose |
|---------|---------|
| `GROUNDED_DOCS_CLI` | Path to built fork binary (optional) |
| `GROUNDED_DOCS_STORE_PATH` | Shared SQLite store for scrape/search |
| `GROUNDED_DOCS_SCRAPE_TIMEOUT_S` | On-demand scrape timeout (default 300) |
| `FRAMEWORK_DOCS_CACHE_PATH` | Optional disk cache directory for normalized responses |

## Cache

In-memory cache (optional disk via `FRAMEWORK_DOCS_CACHE_PATH`) keyed by:

```text
Framework : Framework Version : Topic Hash
```

Invalidates automatically when framework version changes.

## Response normalization

`FrameworkKnowledgeResponse` is the single internal format:

- `metadata` — detector output
- `topic` — agent question
- `provider` — e.g. `grounded_docs`
- `library_id` — resolved doc source
- `content` — documentation text
- `summary` — factual one-liner
- `cached` — whether served from cache

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_detect_framework` | Detector only — no network |
| `perception_framework_docs` | Full pipeline — detect + provider + normalize |

## Future providers

`DocumentationProvider` protocol supports swapping Grounded Docs for:

- Official framework MCPs
- Internal knowledge bases
- Other documentation APIs

Handlers and agents consume `framework_knowledge` only — not provider-specific shapes.

## Requirements / platform support

| Requirement | Notes |
|-------------|--------|
| Node.js **22+** | Verified via `node --version` before CLI calls |
| `npx` on PATH | Auto-augmented on Windows/macOS/Linux common install paths when IDE omits Node from PATH |
| Network | Required for first-time scrape of official docs |
| Disk | Store at `{repo}/artifacts/grounded-docs-store` or `~/.cache/frontend-perception/grounded-docs-store` |

**Cross-platform:** Windows (`npx.cmd` resolved via full path), macOS (Homebrew `/opt/homebrew/bin`), Linux (`/usr/local/bin`). Subprocess uses UTF-8 with replacement on all platforms.

**Graceful degradation:** If Node/npx/network unavailable, `perception_detect_framework` still works; `perception_framework_docs` returns `degraded` codes (`grounded_docs_cli_unavailable`, `node_version_too_old`, etc.) without crashing the MCP.

## Tests

- `tests/test_framework_intelligence.py` — detector + cache
- `tests/test_grounded_docs_reliability.py` — store paths, normalize, Node version parsing
- `src/run_mcp_contract_tests.py` — `detect_framework`, `framework_docs` (graceful if CLI/network unavailable)

## Related

- [tool_reference.md](../tool_reference.md)
- [ADR-013](../design_decisions.md#adr-013-framework-intelligence-provider-abstraction)
