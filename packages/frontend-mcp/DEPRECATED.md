# DEPRECATED — do not publish or install this package.

The separate `frontend-mcp` PyPI alias caused version skew
(`package_version` ≠ `frontend_mcp_version`) in real agent runs.

**Install only:**

```bash
pip install --pre frontend-perception-engine
```

That single package provides:
- all MCP runtime code
- CLI: `frontend-mcp` / `frontend-perception-mcp`
- module: `frontend_mcp` (version mirrors the engine)

If you previously installed the alias:

```bash
pip uninstall frontend-mcp
pip install --pre frontend-perception-engine
```
