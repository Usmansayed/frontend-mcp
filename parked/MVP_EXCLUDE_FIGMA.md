# MVP: Figma Intelligence excluded from MCP

**Status:** Parked (2026-07-23)  
**Package rule:** Do **not** ship Figma Intelligence tools or guides in Frontend Perception MCP until this file is removed or marked lifted.

## Why

MVP focuses on observe / verify / resolve / design / inspiration / snapshot. Figma Intelligence needs PAT setup, southleft/figma-console-mcp, and distracts agents on localhost engineering when inspiration + Design Snapshot already cover design reference.

## What is excluded

- All `perception_figma_*` MCP tools
- MCP resource `perception://figma-guide`
- Module imports of `navigation.figma_intelligence` from the live server
- Coordination “pay Figma family” as an unpaid MVP obligation (deferred in portfolio)

## What remains

- Design reference via `perception_inspiration_*` and/or `perception_build_design_snapshot`
- `compile_figma_seed_spec` in engineering_knowledge (harmless helper; unused until restore)
- Consistency `FigmaKnowledgeSource` (optional payload in context — not MCP tools)

## Where the code lives

`parked/figma_intelligence/` (moved from `src/navigation/figma_intelligence/`).

Imports inside parked files still say `navigation.figma_intelligence` so a restore is a folder move + re-wire.

Handler backup: `parked/mcp_figma_handlers.py.bak`  
Tests: `parked/tests/test_figma_*.py`

## Restore checklist (later)

1. Move `parked/figma_intelligence` → `src/navigation/figma_intelligence`
2. Move tests back from `parked/tests/`
3. Re-add tools in `src/navigation/mcp/tools.py`
4. Restore handlers from `parked/mcp_figma_handlers.py.bak` and dispatch map
5. Re-add `perception://figma-guide` in `resources.py`
6. Re-add `figma_integration` tools in `tool_bindings.v1.yaml`; remove from `DEFERRED_DEFAULT`
7. Put `figma_integration` back on design_reference `resolving_capabilities`
8. Update this file to **Lifted** and refresh README / agent guides
9. Bump package version and publish

**Agent / docs rule**

Until lifted: agents and docs must **not** recommend Figma Intelligence workflows or block MVP tasks on Figma connect/context.
