# Frontend Perception Engine (CRG as Optional Library)

This project implements a frontend navigation layer where:

- Browser Use stays the browser automation engine.
- Code Review Graph (CRG) is used only as an optional knowledge source.
- Browser execution continues even when CRG is unavailable.

## Architecture

```text
Cursor / Claude
   ↓
Our MCP
   ↓
Frontend Navigation Layer
   ↓
Browser Use
   ↓
Browser
```

CRG is integrated behind `ICodeGraph`, so it can be replaced later by another backend such as `FrontendInteractionGraph` without changing Browser Use orchestration.

## Dependency Integration

CRG is integrated as a dependency (not forked, not modified):

- `code-review-graph>=2.3.6`
- `browser-use>=0.13.3`

Install:

```bash
pip install -e .
```

## Frontend Perception MCP (No LLM in Server)

The MCP server is deterministic runtime only (browser observation + actions + verify).  
Your coding agent (Cursor/Claude/Codex) remains the brain.

### Install

Both PyPI names install the same MCP server:

| Package | Install / upgrade |
|---------|-------------------|
| `frontend-perception-engine` | `pip install --upgrade frontend-perception-engine` |
| `frontend-mcp` (alias) | `pip install --upgrade frontend-mcp` |

Use `--upgrade` when a version is already installed — plain `pip install` may leave an older release in place.

**Do not mix** PyPI installs with `pip install -e .` in this repo; editable installs can leave broken metadata that blocks upgrades. Use one or the other.

Recommended (quiet output + next steps):

```bash
uvx --from frontend-perception-engine frontend-perception-install
```

Or the shorter alias name:

```bash
uvx --from frontend-mcp frontend-mcp-install
```

With Chromium for Browser Use:

```bash
uvx --from frontend-perception-engine frontend-perception-install --with-browser
```

Development install from this repo:

```bash
python -m navigation.cli.install --editable .
```

Or classic pip:

```bash
pip install frontend-perception-engine
```

### Run MCP server

Using module entrypoint:

```bash
python -m navigation.mcp
```

Using script entrypoint:

```bash
frontend-perception-mcp
```

Using `uvx` (no local install in current environment):

```bash
uvx --from frontend-perception-engine frontend-perception-mcp
# or
uvx --from frontend-mcp frontend-mcp
```

### Cursor MCP config

```json
{
  "mcpServers": {
    "frontend-perception": {
      "command": "python",
      "args": ["-m", "navigation.mcp"],
      "env": {
        "PYTHONPATH": "C:/Users/usman/Projects/frontend-perception-engine/src"
      }
    }
  }
}
```

### Runtime prerequisites

- Start the sandbox app: `cd sandbox && npm run dev`
- Default URL used by tests/tools: `http://localhost:5173`
- No API keys are required to run the MCP path itself

### Platform documentation

Architecture, roadmap, tool reference, and feature subsystem docs: [docs/README.md](./docs/README.md).

## CRG Documentation and Public API Notes

The integration uses CRG public tool functions from:

- `code_review_graph.tools.build.build_or_update_graph`
- `code_review_graph.tools.query.query_graph`
- `code_review_graph.tools.query.semantic_search_nodes`
- `code_review_graph.tools.query.get_impact_radius`
- `code_review_graph.tools.query.list_graph_stats`
- `code_review_graph.tools.query.traverse_graph_func`

### Graph lifecycle

- Initialize graph (incremental/minimal): `build_or_update_graph(full_rebuild=False, postprocess="minimal")`
- Refresh graph (incremental): `build_or_update_graph(full_rebuild=False)`
- Rebuild graph (full): `build_or_update_graph(full_rebuild=True)`

### Incremental indexing

CRG incremental path is handled by `incremental_update` under the hood and can detect changed files from VCS (`base=HEAD~1` by default).

### Watch mode

CRG supports continuous updates via:

- CLI: `code-review-graph watch`
- API internals: `code_review_graph.incremental.watch` and `start_watch_thread`

This wrapper does not require watch mode, but is compatible with repositories kept fresh by CRG watch/daemon.

### Querying

- Pattern queries (neighbors/file relationships): `query_graph`
- Search (hybrid semantic + keyword): `semantic_search_nodes`
- Blast radius / route impact: `get_impact_radius`
- Traversal/path-like exploration: `traverse_graph_func`
- Stats/health: `list_graph_stats`

## Wrapper Layer

All CRG coupling is isolated in:

`src/navigation/codeGraph/`

Public contract:

- `initialize()`
- `refresh()`
- `rebuild()`
- `search()`
- `shortest_path()`
- `get_neighbors()`
- `get_component()`
- `get_file()`
- `get_route()`
- `query()`

Future-oriented methods are already represented on `ICodeGraph`:

- `findNavigationHint(...)` style equivalent via `find_navigation_hint(...)`
- `find_relevant_components(...)`
- `find_likely_route(...)`
- `find_related_files(...)`
- `find_button_candidates(...)`
- `find_component_hierarchy(...)`
- `find_entry_point(...)`

## Browser Use Integration

`BrowserUseNavigator` provides a lightweight dry-run timeline for tests.

`PerceptionAgentRunner` runs a **real Browser Use agent** with optional graph hints injected via `extend_system_message`. Graph output is never a mandatory stage — if CRG or AWS credentials are missing, the agent either skips hints or reports a clear error.

### Live agent (Bedrock Nova)

1. Start the sandbox:

```bash
cd sandbox && npm run dev
```

2. Configure AWS (copy `.env.example` → `.env`):

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
BEDROCK_MODEL=amazon.nova-pro-v1:0
SANDBOX_URL=http://localhost:5173
```

3. Install AWS extra and run:

```bash
pip install -e ".[aws]"
python src/run_agent.py --task "Add Pulse Watch to cart and complete checkout"
```

Dry-run (graph hints only, no browser):

```bash
python src/run_agent.py --dry-run --task "Log in as admin and open admin report"
```

Flags:

- `--no-graph` — disable CRG hints
- `--headless` — headless browser
- `--max-steps 25` — step limit
- `--url http://localhost:5174` — custom sandbox URL

## Demo

Run:

```bash
python src/demo.py
```

Expected behavior:

1. Browser Use execution starts.
2. Optional code graph query is attempted.
3. Browser Use continues regardless of query success.
