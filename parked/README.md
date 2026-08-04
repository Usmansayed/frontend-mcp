# Parked — not in MVP MCP

Code and docs here are **intentionally excluded** from the production Frontend Perception MCP surface while we ship MVP.

## SEO Intelligence (parked)

| Path | Contents |
|------|----------|
| `parked/seo_intelligence/` | Full former `src/navigation/seo_intelligence/` tree |
| `parked/docs/seo_intelligence.md` | Feature doc |
| `parked/research/seo_intelligence/` | Research notes |
| `parked/tests/` | SEO unit/golden tests + `seo_golden` fixtures |

**Do not** re-register `perception_seo_*` tools, `perception://seo-guide`, or import this package into the MCP server until this exclusion is lifted.

See [MVP_EXCLUDE_SEO.md](MVP_EXCLUDE_SEO.md) for restore steps and product rules.

Lighthouse page audit `perception_audit_seo` (Frontend Quality) remains available — that is **not** SEO Intelligence.

## Figma Intelligence (parked)

| Path | Contents |
|------|----------|
| `parked/figma_intelligence/` | Full former `src/navigation/figma_intelligence/` tree |
| `parked/mcp_figma_handlers.py.bak` | Live MCP handlers before stubbing |
| `parked/tests/test_figma_*.py` | Figma unit tests |

**Do not** re-register `perception_figma_*` tools, `perception://figma-guide`, or import this package into the MCP server until this exclusion is lifted.

See [MVP_EXCLUDE_FIGMA.md](MVP_EXCLUDE_FIGMA.md) for restore steps and product rules.

Design reference remains available via Inspiration Intelligence and Design Snapshot.
