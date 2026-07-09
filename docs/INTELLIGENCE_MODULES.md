# Intelligence Modules Architecture

Frontend Perception MCP is organized as **seven independent intelligence modules** plus a **shared core**. Each module owns its domain and exposes a clean interface; the MCP layer (`navigation/mcp/`) stays thin and delegates to module services.

## Layout

```text
src/navigation/
├── core/                              # Shared infrastructure
├── framework_intelligence/            # 1. Framework detection + docs
├── component_intelligence/            # 2. Component providers + probes
├── design_workflow_intelligence/      # 3. Flows, state, design tools (scaffold)
├── visual_browser_intelligence/         # 4. Browser, observe, verify, visuals
├── codebase_intelligence/             # 5. CRG graph, code ↔ UI
├── frontend_quality_intelligence/     # 6. Console, network, audits, diagnosis
├── design_sense_intelligence/         # 7. Visual heuristics + UX hints
├── mcp/                               # MCP protocol (tools, handlers, server)
└── cli/                               # Install wrapper
```

Legacy import paths (`navigation.perception`, `navigation.console`, `navigation.codeGraph`, etc.) remain as **shims** for backward compatibility.

## Module standard structure

Each intelligence module follows this pattern where applicable:

| Layer | Purpose |
|-------|---------|
| `providers/` | External integrations (Context7, Figma, shadcn, …) |
| `registry.py` | Supported frameworks/tools/services |
| `service.py` | Business logic facade |
| `cache.py` | Module-scoped caching |
| `models.py` | Pydantic/dataclass types |
| `utils.py` | Module helpers |
| `tests/` | Unit tests (repo: `tests/test_<module>.py`) |

MCP tools are registered in `mcp/tools.py` and delegate to module `service.py` via `mcp/handlers.py`.

---

## 1. Framework Intelligence

**Path:** `framework_intelligence/`

Understands the frontend stack and fetches version-aware documentation.

| Capability | Status |
|------------|--------|
| Framework detection | ✅ |
| Version / build tool / package manager | ✅ |
| Project metadata extraction | ✅ |
| Context7 provider | ✅ |
| Documentation cache | ✅ |
| Normalized `FrameworkKnowledgeResponse` | ✅ |

**MCP tools:** `perception_detect_framework`, `perception_framework_docs`

See [features/framework_intelligence.md](./features/framework_intelligence.md).

---

## 2. Component Intelligence

**Path:** `component_intelligence/`

Discovers, selects, installs, and adapts UI components.

| Capability | Status |
|------------|--------|
| Component probes (forms, editors, iframes, scroll, upload) | ✅ |
| Component providers (shadcn, Flowbite, 21st.dev) | 📋 scaffold |
| Component registry | 📋 scaffold |
| Installation / adaptation | 📋 planned |

**MCP tools:** `perception_probe_form` (+ probes via execute_actions)

---

## 3. Design Workflow Intelligence

**Path:** `design_workflow_intelligence/`

Integrates design tools and multi-step workflows.

| Capability | Status |
|------------|--------|
| Flow graphs + runners | ✅ |
| State save/restore | ✅ |
| Auth gates + route guards | ✅ |
| Exploration + feature flags | ✅ |
| Navigation hints (codebase → browser) | ✅ |
| Figma / Penpot / Framer / Excalidraw | 📋 planned |
| Design-to-code, tokens, assets | 📋 planned |

**MCP tools:** `perception_flow_describe`, `perception_state_*`, `perception_auth_gate`, `perception_probe_guards`

---

## 4. Visual & Browser Intelligence

**Path:** `visual_browser_intelligence/`

Interacts with the running application.

| Subpackage | Contents |
|------------|----------|
| `observe/` | scan, observation, preflight |
| `verify/` | SuccessCriteria, verify, JS evaluation |
| `actions/` | scripted_actions |
| `visual/` | screenshots, visual_diff, MCP image responses |
| `live/` | websocket_observer |
| `browser/` | SessionStore, session lifecycle |
| `agent/` | optional Browser Use LLM path |

**MCP tools:** `perception_session_*`, `perception_navigate*`, `perception_observe`, `perception_execute_*`, `perception_verify`

---

## 5. Codebase Intelligence

**Path:** `codebase_intelligence/`

Understands the frontend codebase via Code Review Graph (CRG).

| Capability | Status |
|------------|--------|
| Project / component / route graph | ✅ (CRG) |
| Semantic search | ✅ |
| `ICodeGraph` provider abstraction | ✅ |

**MCP tools:** `perception_code_context`

---

## 6. Frontend Quality Intelligence

**Path:** `frontend_quality_intelligence/`

Validates production readiness and debugging signals.

| Subpackage | Contents |
|------------|----------|
| `console/` | CDP console ring buffer |
| `network/` | CDP network + HAR |
| `audits/` | Lighthouse wrappers |
| `reports/` | diagnosis orchestration |
| `dev_insights.py` | Observe-window quality bridge |
| `diff.py` | Scan regression diff |

**MCP tools:** `perception_console_*`, `perception_network_*`, `perception_audit_*`, `perception_full_diagnosis`, `perception_debug_mode`, `perception_audit_mode`, `perception_diff`

---

## 7. Design Sense Intelligence

**Path:** `design_sense_intelligence/`

Frontend reasoning and UI/UX decision support.

| Capability | Status |
|------------|--------|
| Visual layout heuristics (`visual_insights`) | ✅ |
| Quality report hints (overflow, a11y, perf) | ✅ |
| Layout / typography / color reasoning | 📋 planned |
| Design comparison | 📋 planned |

Consumed during observe (`visual_insights` in observation payload) and diagnosis (`quality_hints`).

---

## Core package

**Path:** `core/`

Shared across modules — no domain intelligence.

| Module | Role |
|--------|------|
| `envelope.py` | MCP contract v1.0 responses |
| `scan_registry.py` | `scan_id` artifact hub |
| `cdp_hub.py` | CDP event multiplexing |
| `artifacts.py` | Artifact path helpers |
| `budget.py` | Output truncation |

---

## Adding a new capability

1. Identify the owning intelligence module.
2. Add logic under that module's `service.py` or subpackage.
3. If external: add a `providers/` implementation + `registry.py` entry.
4. Wire a thin handler in `mcp/handlers.py` and schema in `mcp/tools.py`.
5. Document in `docs/features/<module>.md` and `docs/tool_reference.md`.
6. Add contract test in `src/run_mcp_contract_tests.py`.

Do **not** add domain logic to `mcp/` or `core/`.

---

## Related

- [architecture.md](./architecture.md) — system overview
- [roadmap.md](./roadmap.md) — version milestones
- [design_decisions.md](./design_decisions.md) — ADRs
