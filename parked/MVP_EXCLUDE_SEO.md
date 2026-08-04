# MVP: SEO Intelligence excluded from MCP

**Status:** Parked (2026-07-23)  
**Package rule:** Do **not** ship SEO Intelligence tools or guides in Frontend Perception MCP until this file is removed or marked lifted.

## Why

MVP focuses on observe / verify / resolve / design / inspiration. SEO Intelligence is large (OAuth companions, LibreCrawl, async jobs, AI readiness) and distracts agents on localhost engineering tasks.

## What is excluded

- All `perception_seo_*` MCP tools
- MCP resource `perception://seo-guide`
- Module imports of `navigation.seo_intelligence` from the live server
- Coordination “pay SEO family” as an unpaid MVP obligation (already deferred in portfolio)

## What remains

- `perception_audit_seo` — Lighthouse SEO **category** under Frontend Quality (page-level). Not the SEO Intelligence product.

## Where the code lives

`parked/seo_intelligence/` (moved from `src/navigation/seo_intelligence/`).

Imports inside parked files still say `navigation.seo_intelligence` so a restore is a folder move + re-wire.

## Restore checklist (later)

1. Move `parked/seo_intelligence` → `src/navigation/seo_intelligence`
2. Move tests/docs back from `parked/`
3. Re-add tools in `src/navigation/mcp/tools.py`
4. Re-add handlers (see git history for `handle_seo_*`) and dispatch map
5. Re-add `perception://seo-guide` in `resources.py`
6. Update this file to **Lifted** and refresh README / agent guides
7. Bump package version and publish

**Note (2026-07-23):** After parking, `component_intelligence/.../catalog.py` still imported `default_seo_cache_dir` and crashed MCP startup. Fixed in `1.2.0.dev26` by using a local `.cache` path. Grep for `seo_intelligence` under `src/` before every park/lift.

**Agent / docs rule**

Until lifted: agents and docs must **not** recommend SEO Intelligence workflows or block MVP tasks on SEO evidence.

Strategy must **not** emit `seo_baseline`, `seo_readiness`, or `seo_evidence_collect` as unpaid/next_required (hard-disabled in `engineering_strategy._applies_seo` for MVP).
