# Framework Intelligence (v1)

**Status:** ✅ shipped (v1.0)  
**Module:** `src/navigation/framework_intelligence/`

## Goal

This module does **not** maintain framework knowledge. It only:

1. Detects the project stack from local files
2. Gathers metadata for Context7
3. Returns **normalized** documentation to the host agent

The rest of the MCP never depends on Context7 directly.

## Pipeline

```text
Project (repo_root)
    ↓
Framework Detector
    ↓
Project Metadata
    ↓
Knowledge Provider (Context7 today)
    ↓
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
| Build tool | Vite, Webpack, Rsbuild, Next.js bundler |
| Package manager | npm, pnpm, yarn, bun |
| Language | TypeScript vs JavaScript |
| Monorepo | workspaces, `pnpm-workspace.yaml`, `lerna.json`, `packages/` |
| Rendering | CSR, SSR/SSG hints when detectable |
| Router mode | Next.js App Router vs Pages Router |

## Context7 integration

Provider: `providers/context7.py`

1. Build a rich query from metadata + topic (framework, version, build tool, router, configs)
2. `GET /api/v2/libs/search` — resolve library ID (version-aware when possible)
3. `GET /api/v2/context` — fetch topic-scoped documentation

Set `CONTEXT7_API_KEY` for higher rate limits ([dashboard](https://context7.com/dashboard)).

## Cache

In-memory cache keyed by:

```text
Framework : Framework Version : Topic Hash
```

Invalidates automatically when framework version changes.

## Response normalization

`FrameworkKnowledgeResponse` is the single internal format:

- `metadata` — detector output
- `topic` — agent question
- `provider` — e.g. `context7`
- `library_id` — resolved doc source
- `content` — documentation text
- `summary` — factual one-liner
- `cached` — whether served from cache

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_detect_framework` | Detector only — no network |
| `perception_framework_docs` | Full pipeline — detect + Context7 + normalize |

## Future providers

`KnowledgeProvider` protocol supports:

- Context7 (today)
- Official framework MCPs
- Internal knowledge bases
- Other documentation APIs

Handlers and agents consume `framework_knowledge` only — not provider-specific shapes.

## Tests

- `tests/test_framework_intelligence.py` — detector + cache
- `src/run_mcp_contract_tests.py` — `detect_framework`, `framework_docs` (graceful if Context7 unavailable)

## Related

- [tool_reference.md](../tool_reference.md)
- [ADR-013](../design_decisions.md#adr-013-framework-intelligence-provider-abstraction)
