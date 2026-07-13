# Resolver Intelligence — Agent Guide

Read this before `perception_resolve_*`, `perception_validate_*`, or `perception_correlate_live`.

## What this is

Fast, deterministic code lookups — **no code graph**, no full-repo scan.

| Use MCP resolver | Use host IDE search |
|------------------|---------------------|
| Route → component file | Custom layouts, lazy routes, edge cases |
| Component name → file | Ambiguous `status: ambiguous` results |
| Design token → CSS/tailwind/DTCG | Tokens not in project files |
| Validate your claim | First guess before any resolve |

**Deprecated:** `perception_code_context` (CRG). Prefer resolvers below.

## Always pass `repo_root`

Path to the frontend app root (folder with `package.json`). Default in dev: `sandbox/`.

Env override: `FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT`.

## Standard loop (code ↔ live UI)

```text
1. perception_navigate_and_observe({ url })     → save scan_id
2. perception_resolve_route({
     repo_root, path: "/forms/validation"
   })
   → data.resolution.status, matches[].file_path
3. If status is ambiguous or low_confidence:
     perception_validate_route_claim({ repo_root, claim: { route, file, component } })
4. Edit the matched file in your IDE
5. perception_observe → perception_verify
6. perception_correlate_live({ scan_id, resolution })   → optional DOM cross-check
```

## Resolution envelope

All resolve tools return `data.resolution`:

| Field | Meaning |
|-------|---------|
| `status` | `resolved` \| `ambiguous` \| `not_found` \| `unsupported` \| `low_confidence` |
| `confidence` | `high` \| `medium` \| `low` |
| `matches[]` | `file_path`, `symbol`, `route`, `evidence` |
| `fallback` | When not resolved — `validate_claim` or `host_search` |

**Agent rule:** If `status !== resolved`, follow `fallback` — do not retry the same resolve params.

## Tools

### Routes (React Router v6 static)

```text
perception_resolve_route({ repo_root, path: "/shop/checkout/review" })
perception_validate_route_claim({
  repo_root,
  claim: {
    route: "/forms/validation",
    file: "src/pages/forms/ValidationForm.jsx",
    component: { name: "ValidationForm" }
  }
})
```

### Components

```text
perception_resolve_component({ repo_root, name: "ValidationForm" })
perception_validate_component_claim({
  repo_root,
  claim: { component: { name: "ValidationForm" }, file: "src/pages/forms/ValidationForm.jsx" }
})
```

Uses `components.json` (shadcn) when present, then `src/components/` and `src/pages/`.

### Design tokens

```text
perception_resolve_design_token({ repo_root, token: "accent" })
```

Sources: CSS variables, `tailwind.config.*`, DTCG `tokens.json`.

### State ownership

```text
perception_resolve_state_owner({ repo_root, store_name: "Cart", key: "addItem" })
```

React context, Zustand `create()`, Redux `createSlice()`.

### API endpoints

```text
perception_resolve_api_endpoint({ repo_root, path: "/api/users", method: "GET" })
```

Next.js `app/api/**/route.ts`, Hono routes, fetch references.

### Layout (from design snapshot)

```text
perception_build_design_snapshot({ scan_id })   → snapshot_id (if needed)
perception_resolve_layout({ snapshot_id, region: "sidebar" })
```

### Live correlation

```text
perception_correlate_live({
  scan_id,
  resolution: { matches: [{ symbol: "ValidationForm" }] }
})
```

Checks `dom_text` and `data-testid` from the scan against resolution/claim symbols.

## Performance

- Target: **<200ms** per resolve (thread-offloaded, bounded file reads).
- Call tools **one at a time** — do not batch parallel MCP calls on this server.
- `perception_health` must stay fast during background SEO jobs.

## Hard rules

1. **Observe before correlate** — need `scan_id` from navigate/observe.
2. **Verify after UI edits** — resolvers find files; they do not prove the UI works.
3. **Do not use `perception_code_context`** for route lookup — use `perception_resolve_route`.
4. **Trust `status` + `fallback`** over guessing file paths.
