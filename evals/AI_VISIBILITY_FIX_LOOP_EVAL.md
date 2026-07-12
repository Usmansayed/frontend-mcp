# AI Visibility Fix Loop Eval (E2E-17)

**Goal:** Prove the AI visibility layer runs end-to-end — status exposes the layer, an audit derives the `ai_readiness` block, the graph query returns a well-formed summary, and disabling `include_ai_visibility` removes both the block and the recommendations.

**Prerequisites:**
- Frontend Perception MCP connected
- Internet access for optional live sites (not required — defaults to `https://example.com/` which exercises graceful degraded paths)

---

## Task (give this to the agent)

> Run `perception_seo_status`, then two `perception_seo_audit` calls on the same site — one with `include_ai_visibility: true` and one with `include_ai_visibility: false`. Confirm the first audit produces `reasoning_context_v2.ai_readiness` with `overall_score` and per-dimension results. Query `ai.readiness.summary`. Confirm the second audit has no `ai_readiness` block and no `ai_visibility` recommendations.

---

## Expected agent behavior

| Step | Tool | Pass criteria |
|------|------|---------------|
| 1 | `perception_seo_status` | `data.ai_visibility` block present with phase and analyzer count |
| 2 | `perception_seo_audit` (`include_ai_visibility: true`) | `reasoning_context_v2.ai_readiness` present with dimensions |
| 3 | Inspect `recommendations` | at least one `ai_visibility` recommendation OR non-empty readiness block |
| 4 | `perception_seo_query` (`ai.readiness.summary`) | either computed summary OR `ai_readiness_not_computed_for_this_audit` |
| 5 | `perception_seo_audit` (`include_ai_visibility: false`) | `ai_readiness` block absent; no `ai_visibility` recommendations |

---

## Failure signals

- `include_ai_visibility=false` still emits `ai_readiness`
- Analyzer errors surface as top-level exceptions instead of `degraded[]` notes
- Envelope contains planning hints

---

## Automated golden path

```bash
$env:PYTHONPATH="src"
python src/run_mcp_eval_ai_visibility.py
```

Emits `artifacts/evals/E2E-17/report.json`.
