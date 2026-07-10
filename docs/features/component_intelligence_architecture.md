# Component Intelligence — Complete Architecture

**Status:** Phase 1 search shipped · Phases 2–5 orchestrated via stable contracts (v1.0)  
**Module:** `src/navigation/component_intelligence/`

## Philosophy

> We are **not** searching for the perfect component.  
> We are searching for the **best foundation**, then orchestrating specialized systems to integrate it.

Component Intelligence does **not** install components directly. It **orchestrates a sequence of specialized subsystems** that consult every intelligence module.

| Phase | Role | Status |
|-------|------|--------|
| Search & plan | Find candidates | ✅ |
| Synthesize & select | Merge module guidance → best foundation | ✅ contract-driven |
| Integration pipeline | Docs → plan → deps → compat → install → adapt | ✅ orchestrated (dry-run default) |
| Validate & repair | Browser checks + consult → fix → re-validate | ✅ contract-driven (dry-run default) |

---

## Stable contracts (v1.0)

Component Intelligence **never imports module internals** for orchestration. Each peer module exposes a **stable contract** (`contracts/protocols.py`). Implementations may be heuristic or placeholder today; orchestration does not change when modules mature.

```text
component_intelligence/contracts/
├── protocols.py    # Framework, Codebase, DesignSense, Consistency, Browser
└── registry.py     # IntelligenceContracts.default()

Peer adapters (swap implementation, keep API):
├── framework_intelligence/contract.py
├── codebase_intelligence/contract.py
├── design_sense_intelligence/contract.py
├── consistency_intelligence/contract.py
└── visual_browser_intelligence/contract.py
```

| Contract | Methods | Consumer |
|----------|---------|----------|
| `FrameworkIntelligenceContract` | `evaluate_component`, `fetch_install_documentation`, `plan_framework_repairs` | selection, doc reader, repair |
| `CodebaseIntelligenceContract` | `evaluate_component`, `plan_codebase_repairs` | selection, repair |
| `DesignSenseIntelligenceContract` | `evaluate_component`, `plan_design_repairs` | selection, adapter, repair |
| `ConsistencyIntelligenceContract` | `evaluate_component`, `plan_consistency_repairs` | selection, adapter, repair |
| `BrowserIntelligenceContract` | `validate_component_integration` | browser validator, repair loop |

`IntegrationRequest.execute_install` and `execute_repairs` default to `false` (plan-only). Set `true` to run commands and apply fixes.

---

## Overall pipeline

```text
User Request
      ↓
Search Planner + Provider Search
      ↓
Filtering Pipeline
      ↓
Parallel module guidance
  ├── Framework Intelligence
  ├── Codebase Intelligence
  ├── Design Sense Intelligence
  └── Consistency Intelligence
      ↓
Synthesis (no fixed % weights)
      ↓
Best Foundation
      ↓
Documentation Reader
      ↓
Installation Planner
      ↓
Dependency Resolver
      ↓
Compatibility Resolver
      ↓
Installer
      ↓
Component Adapter
      ↓
Browser Validator
      ↓
Repair Loop (consult → fix → validate)
      ↓
Finished Component
```

---

## 1. Guidance — structured, not scored

Each intelligence module returns **structured guidance**. Component Intelligence **synthesizes** recommendations — no hardcoded 30/25/25/20 weights.

### Framework Intelligence
- `compatible`, `issues`, `compatibility_warnings`
- `required_dependencies`, `peer_dependencies`, `required_configuration`

### Codebase Intelligence
- `existing_patterns`, `reusable_utilities`, `existing_libraries`
- `preferred_implementations`, `duplicate_risks`

### Design Sense Intelligence
- `ux_recommendation`, `layout_recommendation`, `interaction_recommendation`

### Consistency Intelligence
- `required_modifications` + typed adjustments: tokens, spacing, typography, colors, radius, shadows
- **Never hard-rejects** — only modification lists

### Synthesis (`guidance/synthesis.py`)
- `eligible`, `summary`, `strengths`, `concerns`, `rank_factors`
- Ranking uses **priority rules** (framework blockers → issue count → design alignment → adjustment count → duplicates → search relevance)

---

## 2. Integration pipeline — one responsibility per module

```text
integration/
├── documentation_reader.py   # Structured DocumentationBundle
├── installation_planner.py   # InstallationPlan (ordered steps)
├── dependency_resolver.py    # DependencyPlan
├── compatibility_resolver.py # CompatibilityPlan
├── installer.py              # Executes plan via provider
├── component_adapter.py      # Applies module guidance to files
└── pipeline.py               # IntegrationPipeline orchestrator
```

### Documentation Reader
Gathers from: provider metadata, registry JSON, install commands, framework docs (Grounded Docs).  
Extracts: installation steps, dependencies, peer deps, Tailwind plugins, CSS variables, fonts, icons, common issues, breaking changes.

**Output:** `DocumentationBundle`

### Installation Planner
Builds complete execution plan **before** any install:
- install packages / peer deps
- update Tailwind, PostCSS, globals.css
- register CSS variables, fonts, icons

**Output:** `InstallationPlan` with ordered `InstallationStep[]`

### Dependency Resolver
Resolves packages vs existing `package.json`; emits install commands.

### Compatibility Resolver
Tailwind v3/v4, React/Next, icons, animations, plugins, CSS variables — **adapt when possible**.

### Installer
Executes `InstallationPlan` + provider install — **no ad-hoc decisions during install**.

### Component Adapter
Applies Design Sense + Consistency + Codebase guidance to installed files.

---

## 3. Validation & repair

### Browser Validator (`validation/browser_validator.py`)
Checks: console, runtime, hydration, rendering, responsive, a11y, visual (wired to Visual & Quality Intelligence later).

### Repair Loop (`validation/repair_loop.py`)

```text
Install → Validate → Issue?
    → Fix Planner consults:
        Framework Intelligence
        Codebase Intelligence
        Documentation Reader
        (Grounded Docs for docs)
    → Generate FixPlan
    → Apply fix
    → Validate again
```

**Output:** `FixPlan` with `consulted_modules`, `actions`, `documentation_refs`

---

## Module layout

```text
component_intelligence/
├── parser/ planner/ search/     # Phase 1
├── selection/                 # filter + selector
├── guidance/                  # collectors + synthesis
├── integration/               # pipeline subsystems
├── validation/                # browser_validator, fix_planner, repair_loop
├── contracts/                 # stable cross-module protocols + registry
├── orchestrator.py
├── integration_models.py
└── service.py
```

Cross-module: `*/contract.py` on each intelligence module (stable API); `component_guidance.py` holds current heuristic logic.

---

## MCP tools

| Tool | Purpose |
|------|---------|
| `perception_plan_component_search` | ✅ Plan only |
| `perception_search_components` | ✅ Search |
| `perception_select_component_foundation` | Synthesize + select foundation |
| `perception_integrate_component` | Full orchestration pipeline |

---

## Responsibilities (what CI owns)

1. Find the best foundation  
2. Ask every intelligence module for expert guidance  
3. Synthesize recommendations  
4. Plan installation  
5. Install via plan  
6. Resolve dependencies and compatibility  
7. Adapt to design system  
8. Validate in browser  
9. Repair until success or max attempts  

Search is ~10% of the workflow.

---

## Related

- [component_intelligence.md](./component_intelligence.md) — Phase 1 search  
- [TECHNICAL_NARRATIVE.md](../TECHNICAL_NARRATIVE.md)  
- [design_decisions.md](../design_decisions.md#adr-017-component-intelligence-orchestration-refactor)
