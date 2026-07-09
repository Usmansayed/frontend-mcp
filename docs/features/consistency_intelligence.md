# Consistency Intelligence

**Status:** 📋 scaffold only (v1.2)  
**Module:** `src/navigation/consistency_intelligence/`

## Purpose

Consistency Intelligence is the **8th intelligence module**. It ensures the entire frontend remains **mathematically and visually consistent** with the project's design system.

It is **not** responsible for teaching the agent how to design a UI. That belongs to **Design Sense Intelligence** (qualitative UX reasoning, heuristics, layout guidance).

| Module | Question it answers |
|--------|---------------------|
| **Design Sense Intelligence** | "Is this good UX? What should the agent consider?" |
| **Consistency Intelligence** | "Does this match the design system? What is inconsistent and how severe?" |

## Planned scope

Future analysis and validation across:

- Design tokens (CSS variables, theme files, Tailwind config)
- Spacing systems and rhythm
- Typography scales and font usage
- Color usage and semantic roles
- Border radius and shadow tokens
- Layout grids and breakpoints
- Component visual parity (buttons, inputs, cards, …)
- Interaction states (hover, focus, active, disabled)
- Visual hierarchy consistency
- Responsive consistency across viewports

## Planned outputs

```text
Code + computed styles + screenshots
    ↓
Token / rule extraction
    ↓
Cross-surface comparison (code ↔ DOM ↔ design files)
    ↓
ConsistencyReport (findings + scores)
    ↓
Agent (and future auto-fix suggestions)
```

### Future response shape (illustrative)

- `ConsistencyReport` — overall score, per-category scores
- `ConsistencyFinding` — rule id, severity, locations (file + selector + scan), expected vs actual
- `degraded` — when token source or browser observation unavailable

## Module layout (scaffold)

```text
consistency_intelligence/
├── models.py          # ConsistencyReport, ConsistencyFinding (planned)
├── service.py         # ConsistencyIntelligenceService facade
├── rules/             # Per-domain validators (planned)
│   ├── tokens/
│   ├── spacing/
│   ├── typography/
│   ├── color/
│   ├── layout/
│   ├── components/
│   └── states/
├── providers/         # Figma tokens, Style Dictionary, etc. (planned)
├── registry.py        # Supported design-system formats (planned)
└── cache.py           # Snapshot caching (planned)
```

## MCP tools (planned)

| Tool | Purpose |
|------|---------|
| `perception_consistency_audit` | Full consistency scan for current route / component |
| `perception_consistency_diff` | Compare consistency between two scans or branches |
| `perception_token_snapshot` | Extract design tokens from code + computed styles |

Not registered yet — scaffold only.

## Dependencies on other modules

| Module | Role |
|--------|------|
| Visual & Browser Intelligence | DOM snapshots, computed styles, screenshots |
| Codebase Intelligence | Source files, component graph, theme paths |
| Design Workflow Intelligence | Figma / design-file token import (future) |
| Framework Intelligence | Stack-aware token locations (Tailwind, CSS modules, …) |

## Explicit non-goals

- UX coaching or aesthetic opinions → **Design Sense Intelligence**
- Lighthouse a11y/SEO scores → **Frontend Quality Intelligence**
- Functional correctness → **Visual & Browser Intelligence** (`perception_verify`)

## Related

- [INTELLIGENCE_MODULES.md](../INTELLIGENCE_MODULES.md)
- [design_decisions.md](../design_decisions.md#adr-015-consistency-intelligence-vs-design-sense)
