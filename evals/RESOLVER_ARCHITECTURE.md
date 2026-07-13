# Resolver Architecture — Phase 2 Design

**Date:** 2026-07-13  
**Status:** Design only — **freeze this contract before any parser code**  
**Prerequisite:** Phase 1 async execution model complete ([`ASYNC_EXECUTION_MODEL.md`](ASYNC_EXECUTION_MODEL.md))  
**Parent:** [`ARCHITECTURE_RETHINK.md`](ARCHITECTURE_RETHINK.md)

---

## Directive

> **Do not start coding `resolve_route` yet.**  
> First design the Resolver Architecture as a reusable subsystem.  
> The parser is ~10–20% of the work; the abstraction is what will last.

Phase 2 order:
1. Freeze this document + contracts
2. Implement **reference resolver**: React Router (static `createBrowserRouter` / route config)
3. Extend plugins: Next.js App Router, Remix, TanStack Router
4. Replace `perception_code_context` MCP surface with `resolve_*` / `validate_*` tools
5. Phase 3: remaining resolvers on same contract

---

## 1. What is a resolver?

A **resolver** is a **deterministic, bounded** function that maps a **typed query** + **repo context** to a **structured result** without building a code graph or scanning the whole repository.

| Resolver IS | Resolver IS NOT |
|-------------|-----------------|
| Fast (<200ms target) | Full AST / call graph |
| Framework-pluggable | Semantic / embedding search |
| Reads known config files only | `rglob` over entire repo |
| Returns evidence + confidence | LLM reasoning |
| Composable with validators | Replacement for host grep |

**Examples:**
- `RouteResolver`: `/forms/validation` → `ValidationForm.jsx`
- `DesignTokenResolver`: `primary` → `#3b82f6` from `tailwind.config.ts`
- `ComponentResolver`: `Button` → `components/ui/button.tsx` via `components.json`

---

## 2. ResolverContract (every resolver implements)

### 2.1 Protocol interface

```python
# Conceptual — package: navigation.resolver_intelligence

class ResolverKind(str, Enum):
    ROUTE = "route"
    COMPONENT = "component"
    API_ENDPOINT = "api_endpoint"
    DESIGN_TOKEN = "design_token"
    LAYOUT = "layout"
    STATE_OWNER = "state_owner"

class ResolverContract(Protocol):
    kind: ResolverKind

    def supported_frameworks(self) -> list[str]:
        """e.g. ['react-router-v6', 'next-app-router']"""

    def can_handle(self, ctx: ResolverContext) -> bool:
        """Cheap pre-check: framework detected, required files exist."""

    def resolve(self, query: ResolverQuery, ctx: ResolverContext) -> ResolverResult:
        """Sync, bounded work — MUST complete <200ms or return ambiguous/timeout."""
```

### 2.2 Context (`ResolverContext`)

```python
@dataclass(frozen=True)
class ResolverContext:
    repo_root: Path
    framework: FrameworkDetection | None  # from detect_framework
    repo_layout: RepoLayoutHints          # app dir, src dir, router file candidates
```

Built once per MCP call from:
- `perception_detect_framework` output (cached per `repo_root` for session)
- Fixed file existence checks (no graph)

### 2.3 Query (`ResolverQuery`)

```python
@dataclass
class ResolverQuery:
    kind: ResolverKind
    params: dict[str, Any]   # kind-specific, validated by schema
    hints: dict[str, Any]    # optional host hints (non-authoritative)
```

Kind-specific params examples:

| Kind | Required params | Optional |
|------|-----------------|----------|
| ROUTE | `path: str` | `method` (for API routes) |
| COMPONENT | `name: str` | `export` |
| DESIGN_TOKEN | `token: str` | `category` (color, spacing) |
| API_ENDPOINT | `path: str` | `method` |
| STATE_OWNER | `key: str` | `store_name` |
| LAYOUT | `snapshot_id` or `scan_id` | `region` |

### 2.4 Result (`ResolverResult`) — unified schema

```python
@dataclass
class ResolverResult:
    ok: bool
    kind: ResolverKind
    status: ResolverStatus          # see §4
    confidence: ConfidenceLevel     # see §5
    matches: list[ResolverMatch]    # 0..N (N>1 → ambiguous)
    evidence: list[EvidenceRef]     # file, line, snippet
    degraded: list[str]
    latency_ms: int
    resolver_id: str                # e.g. "react-router-v6.static"
    fallback: FallbackHint | None   # see §6
```

```python
@dataclass
class ResolverMatch:
    summary: str
    file_path: str
    symbol: str | None              # component name, handler fn, token name
    line_start: int | None
    line_end: int | None
    route: str | None               # for ROUTE kind
    metadata: dict[str, Any]        # framework-specific extras
```

All MCP `perception_resolve_*` tools return this schema nested under `data.resolution`.

---

## 3. Plugin model (framework resolvers)

### 3.1 Registry

```text
ResolverRegistry
  ├── register(RouteResolverPlugin)      # one per framework
  ├── register(DesignTokenResolverPlugin)
  └── resolve(query, ctx) → ResolverResult
        1. Filter plugins where can_handle(ctx)
        2. Sort by priority (framework match strength)
        3. Run first plugin; if ambiguous, try next or merge
```

### 3.2 Route plugin interface

```python
class RouteResolverPlugin(ResolverContract):
    kind = ResolverKind.ROUTE
    priority: int  # higher = preferred when multiple match

    def router_file_candidates(self, ctx: ResolverContext) -> list[Path]:
        """e.g. [src/router.jsx, src/App.tsx, app/routes.ts]"""

    def resolve_route(self, path: str, ctx: ResolverContext) -> ResolverResult:
        ...
```

### 3.3 Framework plugins (implementation order)

| Plugin ID | Framework signal | Router source files | Phase |
|-----------|------------------|---------------------|-------|
| `react-router-v6.static` | `react-router-dom` in deps | `router.jsx`, `routes.tsx`, inline in `App` | **Reference** |
| `next-app-router.static` | `next` + `app/` dir | `app/**/page.tsx` filesystem routes | 2b |
| `remix.static` | `@remix-run/react` | `app/routes/*.tsx` | 2c |
| `tanstack-router.static` | `@tanstack/react-router` | `routeTree.gen.ts`, `routes/` | 2d |

Each plugin:
- Reads **only** declared router files + route directory (bounded file count cap, e.g. 200 files for Next app dir)
- No CRG, no tree-sitter fleet
- Runs in **SYNC_OFFLOAD** thread pool (Phase 1 runtime)

### 3.4 Detection integration

Reuse `FrameworkIntelligenceService.detect()` — resolvers do not re-detect unless `framework` omitted from context.

---

## 4. Ambiguity model (`ResolverStatus`)

```python
class ResolverStatus(str, Enum):
    RESOLVED = "resolved"           # exactly one high-confidence match
    AMBIGUOUS = "ambiguous"         # multiple plausible matches
    NOT_FOUND = "not_found"         # searched, nothing matched
    UNSUPPORTED = "unsupported"     # framework not handled by any plugin
    LOW_CONFIDENCE = "low_confidence"  # single match but weak signal
    ERROR = "error"                 # parse failure, missing files
```

**Agent-facing rule (AGENT_GUIDE):**

| Status | Next step |
|--------|-----------|
| `resolved` | Proceed to observe / correlate_live |
| `ambiguous` / `low_confidence` | Host search OR `validate_*_claim` |
| `not_found` | Host grep; do not retry resolve with same params |
| `unsupported` | Host search required |

---

## 5. Confidence model

```python
class ConfidenceLevel(str, Enum):
    HIGH = "high"       # static parse, exact path match, single candidate
    MEDIUM = "medium"   # inferred dynamic segment, alias file
    LOW = "low"         # heuristic, partial file match
    NONE = "none"       # not_found / error
```

**Scoring factors (deterministic, no ML):**

| Factor | Weight |
|--------|--------|
| Exact route path match in static config | +0.5 |
| Import resolves to file on disk | +0.3 |
| Framework plugin exact match | +0.1 |
| Dynamic segment (`:id`) in pattern | −0.2 |
| Multiple equally good matches | → `ambiguous` |

Expose `confidence_score: float` (0–1) in `ResolverResult` for tooling; agent uses `confidence` enum.

---

## 6. Fallback strategy

```python
@dataclass
class FallbackHint:
    strategy: Literal["validate_claim", "host_search", "correlate_live_only"]
    message: str
    suggested_tools: list[str]
```

**Decision tree:**

```text
resolve(query)
  ├─ status=resolved, confidence=high → done
  ├─ status=ambiguous → fallback: validate_claim OR host_search
  ├─ status=low_confidence → fallback: validate_claim
  ├─ status=not_found → fallback: host_search
  └─ status=unsupported → fallback: host_search (no MCP graph)
```

**Never:** fall back to CRG / full graph build.

---

## 7. Validation integration (`validate_*`)

Validators are **siblings**, not subclasses of resolvers. They share result schema but different input.

### 7.1 ValidatorContract

```python
class ValidatorContract(Protocol):
    claim_type: str  # "route_component", "component_file", ...

    def validate(self, claim: AgentClaim, ctx: ResolverContext) -> ValidationResult:
        ...
```

### 7.2 `ValidationResult`

```python
@dataclass
class ValidationResult:
    valid: bool
    checks: list[CheckResult]   # { name, passed, detail }
    mcp_resolve: ResolverResult | None  # optional cross-check
    normalized_match: ResolverMatch | None
```

**Checks (route_component claim):**
1. `claim.file` exists under `repo_root`
2. `claim.component.name` in file content (bounded read, first 50KB)
3. `resolve_route(claim.route)` agrees OR `evidence` snippets match file lines
4. Optional: import chain from router file to component file (single-hop read, no graph)

### 7.3 Composition: `resolve` + `validate`

```text
perception_resolve_route(path)
  → ResolverResult

perception_validate_route_claim(claim)
  → ValidationResult (may call resolve_route internally for cross-check)

perception_correlate_live(scan_id, resolution | claim)
  → LiveCorrelationResult (DOM markers vs expected component)
```

**Unified orchestrator (optional thin facade):**

```text
perception_resolve_with_fallback(kind, params)
  1. result = registry.resolve(...)
  2. if result.status in (ambiguous, low_confidence, not_found):
       return result + fallback hint (no auto-validate — host must supply claim)
  3. else return result
```

Do not auto-invoke host; return `fallback` hints in envelope for agent to act on.

---

## 8. MCP tool mapping (Phase 2–3)

| MCP tool | Kind | Phase |
|----------|------|-------|
| `perception_resolve_route` | ROUTE | 2 (reference plugin) |
| `perception_validate_route_claim` | validation | 2 |
| `perception_resolve_component` | COMPONENT | 3 |
| `perception_validate_component_claim` | validation | 3 |
| `perception_resolve_api_endpoint` | API_ENDPOINT | 3 |
| `perception_resolve_design_token` | DESIGN_TOKEN | 3 |
| `perception_resolve_layout` | LAYOUT | 3 |
| `perception_resolve_state_owner` | STATE_OWNER | 3 |
| `perception_correlate_live` | live bridge | 3 |

**Deprecate:** `perception_code_context` → returns `degraded: ["use_perception_resolve_route"]` during migration.

---

## 9. Execution integration (Phase 1 dependency)

All resolvers:
- **Tier:** `SYNC_OFFLOAD` (thread pool)
- **Timeout:** 2s hard cap per resolve call
- **Cancellation:** honor token between file reads
- **No event loop blocking**

If resolve exceeds 2s → `status=error`, `degraded: ["resolver_timeout"]`, `fallback: host_search`.

---

## 10. Package layout (proposed)

```text
src/navigation/resolver_intelligence/
  __init__.py
  contracts.py          # ResolverContract, ValidatorContract, dataclasses
  registry.py           # ResolverRegistry
  context.py            # ResolverContext builder
  confidence.py           # scoring
  orchestrator.py         # resolve_with_fallback
  plugins/
    route/
      react_router_v6.py  # reference implementation
      next_app_router.py
      remix.py
      tanstack.py
    component/
      shadcn.py
    design_token/
      tailwind.py
      dtcg.py
  validators/
    route_claim.py
    component_claim.py
  live/
    correlate.py          # scan_id + resolution
```

**Separate from** `codebase_intelligence/` (CRG) — eventual CRG removal does not break resolvers.

---

## 11. Reference implementation scope (React Router v6)

**In scope for first plugin:**
- `createBrowserRouter([...])` array in dedicated router file
- Nested `children` paths
- `element: <Component />` and `element: <Navigate />`
- Path join for nested routes (`/forms/validation`)

**Out of scope (→ ambiguous / validate_claim):**
- Lazy `React.lazy(() => import(...))`
- Data routers with loaders only (no element)
- Code-split route modules spread across files
- React Router data APIs (`createRoutesFromElements` with dynamic JSX)

**Output example:**

```json
{
  "ok": true,
  "data": {
    "resolution": {
      "status": "resolved",
      "confidence": "high",
      "confidence_score": 0.95,
      "matches": [{
        "summary": "ValidationForm renders /forms/validation",
        "file_path": "src/pages/forms/ValidationForm.jsx",
        "symbol": "ValidationForm",
        "route": "/forms/validation",
        "line_start": 89,
        "metadata": { "router_file": "src/router.jsx" }
      }],
      "evidence": [{ "file": "src/router.jsx", "line": 89, "snippet": "element: <ValidationForm />" }],
      "resolver_id": "react-router-v6.static",
      "latency_ms": 42
    }
  }
}
```

---

## 12. Phase 3 resolvers (same contract)

After React Router reference + framework route plugins:

| Resolver | Plugin approach |
|----------|-----------------|
| `resolve_component` | `components.json` + folder conventions (shadcn) |
| `resolve_design_token` | tailwind.config + CSS vars + DTCG JSON |
| `resolve_layout` | Read from `DesignSnapshot` registry (no repo walk) |
| `resolve_state_owner` | Shallow parse known store files (zustand create, redux slice) |
| `resolve_api_endpoint` | Bounded scan of `app/api`, `pages/api`, `src/routes` patterns |
| `correlate_live` | DOM query from scan + match text/testid vs resolution |

All share `ResolverResult` / evidence / confidence / fallback.

---

## 13. Open questions (freeze before coding)

| # | Question | Proposed answer |
|---|----------|-----------------|
| 1 | Max files per resolve call? | 50 reads, 2MB total read cap |
| 2 | Multiple plugins match framework? | Highest `priority` wins; if tie → `ambiguous` |
| 3 | Host `hints` in query? | Non-authoritative; logged in evidence |
| 4 | Monorepo `repo_root`? | Required param; no cwd fallback |
| 5 | Sync vs async resolver API? | Sync body + SYNC_OFFLOAD wrapper only |

---

## 14. Success criteria (Phase 2)

- [ ] Contract frozen in `contracts.py` + this doc
- [ ] React Router plugin passes sandbox E2E (`/forms/validation` → `ValidationForm.jsx`)
- [ ] p95 `resolve_route` <200ms on sandbox
- [ ] `ambiguous` and `fallback` returned correctly for lazy-route fixture
- [ ] `perception_code_context` deprecated with migration message
- [ ] No CRG import in resolver package

---

## 15. Explicit non-goals (Phase 2)

- ❌ Next/Remix/TanStack plugins until React Router reference merged
- ❌ Semantic search / embeddings
- ❌ Call graph / impact radius
- ❌ SEO async jobs (Phase 1)
- ❌ Auto host-agent callbacks

---

## Recommendation to implementers

> Freeze `ResolverContract`, `ResolverResult`, ambiguity/confidence enums, and plugin registry **before** writing parsers.  
> Implement **React Router v6 static** as the reference plugin.  
> Parallel track: Phase 1 async execution must land first so resolvers never block stdio.
