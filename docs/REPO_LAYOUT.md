# Repository layout

What ships in the **MCP package** vs what is **dev-only** in this monorepo.

## MCP package (`pip install` / `frontend-perception-mcp`)

Only `src/navigation/` is published. Entry point:

```text
frontend-perception-mcp → navigation.mcp.server:main
```

Bundled with the wheel:

- `src/navigation/mcp/AGENT_GUIDE.md` — `perception://agent-guide`
- `src/navigation/mcp/evals/` — eval scenario docs
- `src/navigation/*/docs/*_AGENT_GUIDE.md` — module playbooks

Not in the package:

| Path | Purpose |
|------|---------|
| `sandbox/` | Local Vite test app (contract/eval runs) |
| `tests/` | Pytest suite |
| `src/run_*.py` | Dev validation runners |
| `coordination_layer/` | Runtime artifacts + research (coordination) |
| `execution_layer/` | EVW workflow definitions |
| `evals/` | Validation docs + generated reports |
| `references/` | External study clones (read-only) |
| `research/` | Design notes + optional local repo clones |
| `design_benchmarks/` | Consistency benchmark fixtures |
| `packages/frontend-mcp/` | PyPI alias meta-package |
| `artifacts/`, `.cache/` | Local runtime output (gitignored) |

## Local cleanup

Safe to delete anytime (regenerated):

```bash
# PowerShell
Remove-Item -Recurse -Force artifacts, .cache, .code-review-graph, .pytest_cache, dist, browser-use -ErrorAction SilentlyContinue
```

## Default `repo_root` for code tools

Installed MCP uses `cwd` unless set:

```bash
FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT=/path/to/your/frontend
```

In this repo checkout, dev mode still defaults to `sandbox/` when present.
