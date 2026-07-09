# Audits subsystem

**Status:** ✅ shipped (v0.6)  
**Module:** `src/navigation/audits/`

## Tools (shipped)

| MCP tool | Engine | Output |
|----------|--------|--------|
| `perception_audit_accessibility` | Lighthouse a11y | `AuditReport` |
| `perception_audit_performance` | Lighthouse performance | scores + metrics |
| `perception_audit_seo` | Lighthouse SEO | issues list |
| `perception_audit_best_practices` | Lighthouse BP | issues list |

**Requires:** Node.js 18+ (`npx lighthouse@12`). Optional pip extra: `pip install frontend-perception-engine[audits]` (documents requirement; no extra Python deps).

Lighthouse runs in a **dedicated headless Chrome** (via `--preset=desktop`) against the session URL — avoids CDP conflicts with the managed Browser Use session.

## Principles

1. **Our schema** — agents consume structured JSON, not raw Lighthouse HTML.
2. **No extension** — Lighthouse runs against CDP URL from managed browser (same pattern as Puppeteer).
3. **Blocking vs advisory** — map audit severity to `agent_summary.blocking` where appropriate.

## Report shape (draft)

```json
{
  "audit": {
    "category": "accessibility",
    "score": 0.92,
    "blocking": [],
    "warnings": [{"id": "color-contrast", "title": "...", "selector": "..."}],
    "metrics": {},
    "artifacts": {"lighthouse_json": "perception://scan/{id}/lighthouse.json"}
  }
}
```

## Reference study

`references/browser-tools-mcp/browser-tools-server/lighthouse/` — audit modes, Next.js-specific prompts. Reimplement runners without copying server middleware.

## Orchestration

- `perception_audit_mode` — all categories (v0.7)
- `perception_full_diagnosis` — observe + console + network + audits + visual (v0.7)

## Tests

- Smoke on static HTML fixture (known a11y violation)
- Skip in CI if Lighthouse not installed (marker)

## Related

- [reports.md](./reports.md)
- [verification.md](./verification.md) — agent criteria after audit fixes
