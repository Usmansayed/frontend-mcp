# 03 — Families and Episode Portfolio

**Source of truth:** `src/navigation/coordination_intelligence/planning/episode_portfolio.py`

## Capability → family map (code)

| Capability ID | Family |
|---------------|--------|
| `browser_observe` | observe |
| `browser_verify` | verify |
| `inspiration_workflow` | inspiration |
| `figma_integration` | figma |
| `design_snapshot` | snapshot |
| `component_select` / `component_search_plan` | component |
| `design_review` | design_review |
| `resource_workflow` | resources |
| `seo_audit` | seo |
| `resolver_route` / `resolver_component` | resolve |
| `form_probe` | forms |
| `guard_probe` | guards |

**Also appear as unpaid (gate-driven, not always in CAPABILITY_FAMILY):**

| Family | When unpaid |
|--------|-------------|
| `sections` | `section_checklist_required` |
| `residue` | `residue_scan_required` |
| `design_review` | `ship_council_required` |

## When unpaid is set (logic)

| Trigger | Unpaid family | Notes |
|---------|---------------|-------|
| Unresolved `design_reference` | `inspiration` (if no snap/figma paid) | Snapshot listed separately |
| Unresolved `design_reference` | `snapshot` | “can supersede inspiration” |
| Unresolved `component_foundation` | `component` | |
| Unresolved `verification_outcome` | `verify` | |
| Unresolved `layout_shell` + no observe | `observe` | **Likely dead path** — `layout_shell` not emitted by current `_DECISION_RULES` (see [Research situation evidence paths](a66ea78d-aab1-4d98-a5dc-9af725a73dd2)) |
| Section checklist required | `sections` | Distinct from page verify |
| Residue required | `residue` | Remeasure even if prior snapshot paid |
| Ship council required | `design_review` | |
| After insp/snap paid, no observe yet | `observe` nudge | Suppressed during section/ship ladder |

## When portfolio is empty

`compile_episode_portfolio` returns empty unpaid when **`design_scope_applies()` is false** (outside design_driven / redesign / system_setup / structural|balanced design initiative). Note: `"N/A outside design scope"`.

**Guide implication:** Feature/hotfix agents cannot rely on unpaid alone — class tables still apply.

## Paid

Capability ledger entries with `succeeded` / `provisional` or `advancement_eligible=true` (not `failed`/`noop`).

## Supersede rules agents must know

1. **Snapshot or Figma paid** → inspiration not nagged for design_reference.  
2. **Page verify paid** ≠ sections paid.  
3. **Prior snapshot paid** ≠ residue closed.  
4. Portfolio is **advisory** in MCP (not a claim gate) — agent rule must make it **binding in behavior**.

## Guide design implications

- Use **family names** in guides (observe, snapshot, …), map 1–2 example tools.  
- Teach supersede explicitly (mockup → snapshot wins over inspiration).  
- Separate **sections** and **ship** from verify in Done ladder language.  
- Never tell agents SEO is required by default.
- When unpaid empty: still classify task and run min evidence path.
