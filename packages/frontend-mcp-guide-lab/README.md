# frontend-mcp-guide-lab (DEV ONLY)

Separate from production **`frontend-mcp`**.

Serves `guide-lab://` markdown resources for the large-docs vs clean-guides experiment.

```bash
# from repo root
set PYTHONPATH=src
python -m navigation.guide_lab.mcp_server

# quizzes
python -m navigation.guide_lab.runner
```

Do **not** point Cursor’s primary Frontend MCP at this package.
