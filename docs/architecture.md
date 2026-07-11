# Architecture

**Packages:** `frontend-perception-engine`, `frontend-mcp` (alias)  
**MCP server version:** 0.11.0  
**Python package version:** 0.2.0+

> **See also:** [INTELLIGENCE_MODULES.md](./INTELLIGENCE_MODULES.md) — the canonical map of all intelligence modules.

## North star

The **ultimate Frontend MCP** for AI coding agents: perception, debugging, verification, and workflow — not a BrowserTools clone, not a Playwright wrapper, not an autonomous browser agent.

```text
Cursor / Claude / Codex  (brain — plans, edits code)
        ↓
Frontend Perception MCP  (deterministic runtime — no LLM)
        ↓
Intelligence Modules + Core
        ↓
Browser Use + CDP        (Chromium control)
        ↓
Your app (localhost or deployed)
```

## Intelligence module layout (v0.13)

```text
src/navigation/
├── core/                         # envelope, scan registry, CDP hub, budgets
├── framework_intelligence/       # stack detection + on-demand docs
├── component_intelligence/       # component orchestration + providers
├── design_workflow_intelligence/ # flows, state, auth, exploration
├── visual_browser_intelligence/  # observe, verify, browser, agent
├── design_snapshot_engine/       # extract → normalize DesignSnapshot
├── design_reference_registry/    # reference snapshots + compare
├── codebase_intelligence/        # CRG graph, code context
├── frontend_quality_intelligence/# console, network, audits, diagnosis
├── design_sense_intelligence/    # UX heuristics, design reasoning
├── consistency_intelligence/     # Project Design Graph + consistency
├── inspiration_intelligence/       # Public gallery inspiration (Dribbble, Behance, …)
├── figma_intelligence/           # User Figma account + design systems
├── mcp/                          # MCP server (thin handlers)
└── cli/
```

Legacy paths (`perception/`, `console/`, `codeGraph/`, `browser_use/`, etc.) are **import shims** — prefer intelligence module imports for new code.

## Module boundaries: Design Sense vs Consistency

| Concern | Module |
|---------|--------|
| "Is this good UX?" / qualitative guidance | **Design Sense Intelligence** |
| "Does this match the design system?" / token & scale enforcement | **Consistency Intelligence** |

## Core principles

1. **Deterministic MCP** — tools return facts; playbooks live in `AGENT_GUIDE.md`.
2. **Modular intelligence** — extend one module without touching unrelated code.
3. **Provider abstraction** — external services (Grounded Docs, Lighthouse, CRG) behind provider interfaces.
4. **CDP-first** — console, network, screenshots, audits via Chrome DevTools Protocol.
5. **Verify before done** — `perception_verify` + `perception_diff` are first-class.

## Session lifecycle

```mermaid
sequenceDiagram
    participant Agent as Host agent
    participant MCP as Perception MCP
    participant VB as Visual Browser Intelligence
    participant BU as Browser Use
    participant App as Your app

    Agent->>MCP: perception_session_start
    MCP->>VB: SessionStore.start()
    VB->>BU: launch Chromium
    Agent->>MCP: perception_navigate_and_observe
    MCP->>VB: scan_page + observe
    VB->>App: CDP navigate + snapshot
    MCP-->>Agent: agent_summary + images + scan_id
    Agent->>MCP: perception_verify
    MCP-->>Agent: pass/fail + visuals
```

## Related

- [INTELLIGENCE_MODULES.md](./INTELLIGENCE_MODULES.md)
- [tool_reference.md](./tool_reference.md)
- [roadmap.md](./roadmap.md)
- [features/consistency_intelligence.md](./features/consistency_intelligence.md)

