# Guide Lab (EXP-026) — Option C dual guides

**Production always-on** is now the short contract; situation cards live at `perception://guide/*`.

## Run quizzes

```bash
set PYTHONPATH=src
python -m navigation.guide_lab.runner
```

Latest: **B 48/48**, A 2/48. See `scorecard.md`.

## Dev MCP (optional)

```bash
python -m navigation.guide_lab.mcp_server
```

Separate from production `frontend-mcp` browser tools — resources only.
