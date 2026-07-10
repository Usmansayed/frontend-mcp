# MCP tool reference

All tools return JSON envelope `contract_version: "1.0"` plus optional inline PNG images (v0.2+).

Common fields: `ok`, `tool`, `session_id`, `run_id`, `scan_id`, `url`, `error`, `degraded`, `data`.

## Bootstrap

### `perception_health`

Check dev server HTTP reachability before work.

| Param | Type | Required |
|-------|------|----------|
| `url` | string | no (default `http://localhost:5173`) |

### `perception_session_start`

Start managed Chromium session.

| Param | Type | Default |
|-------|------|---------|
| `base_url` | string | `http://localhost:5173` |
| `headless` | bool | `true` |
| `viewport.width` / `height` | int | 1920 / 1080 |

### `perception_session_end`

| Param | Required |
|-------|----------|
| `session_id` | yes |

## Observation

### `perception_navigate`

Navigate only; pair with `perception_observe` for snapshot.

### `perception_navigate_and_observe` / `perception_observe`

| Param | Values | Notes |
|-------|--------|-------|
| `include_screenshot` | bool | default true |
| `screenshot_mode` | `viewport` \| `full` \| `element` | |
| `screenshot_selector` | CSS string | required for `element` |
| `annotate_screenshot` | bool | default true |
| `detail` | `full` \| `summary_only` | summary still returns `visual` + images |
| `budget` | object | cap a11y/dom chars |

**Returns:** `data.agent_summary`, `data.visual`, optional `data.observation`, inline images.

## Action

### `perception_execute_script`

| Param | Required |
|-------|----------|
| `session_id`, `script` | yes |
| `capture_insights_during` | no (default true) |

### `perception_execute_actions`

Actions: `click_button`, `click_link`, `set_input` (with `text` / `label` / `value`).

## Verification

### `perception_verify`

Criteria: `url_contains`, `text_contains`, `js_assertions`, etc.

On failure: `failure_scan_id`, inline annotated screenshot.

### `perception_diff`

| Param | Required |
|-------|----------|
| `scan_id_before`, `scan_id_after` | yes |

Returns text diff + `visual_diff` + inline side-by-side/heatmap when screenshots exist.

## Probes & safety

| Tool | Purpose |
|------|---------|
| `perception_auth_gate` | Login/MFA/CAPTCHA → `requires_human` |
| `perception_probe_form` | Form validation probe |
| `perception_probe_guards` | Route guard suite (`mode`: maze \| routes) |

## State & flows

| Tool | Purpose |
|------|---------|
| `perception_state_save` / `restore` / `list` | Cookie/storage snapshots |
| `perception_flow_describe` | Flow checkpoint graph |

## Code context

### `perception_code_context`

| Param | Default |
|-------|---------|
| `repo_root` | sandbox/ |
| `query_type` | `stats` |
| `query_kwargs` | {} |

## Console (v0.4+)

### `perception_console_get`

| Param | Notes |
|-------|-------|
| `session_id` | required |
| `levels` | e.g. `["error","warn","log"]` |
| `contains` | case-insensitive substring |
| `since_index` | absolute session entry index |
| `limit` | default 100 |

### `perception_console_clear`

Wipes session console ring buffer.

## Network (v0.5+)

### `perception_network_get`

| Param | Notes |
|-------|-------|
| `session_id` | required |
| `failed_only` | bool |
| `api_group` | e.g. `dev-insights-ok` |
| `contains` | URL substring |
| `status_min` / `status_max` | HTTP status range |
| `since_index` | absolute session entry index |
| `limit` | default 50 |
| `include_bodies` | fetch response bodies (64KB cap) |

### `perception_network_clear`

Wipes session network ring buffer.

## Audits (v0.6+, requires Node.js)

### `perception_audit_accessibility` / `perception_audit_performance` / `perception_audit_seo` / `perception_audit_best_practices`

| Param | Notes |
|-------|-------|
| `session_id` | required |
| `url` | optional; defaults to current page |
| `timeout_s` | default 120 |

Returns `data.audit` (full report) and `data.agent_summary` with `audit.score`, `blocking`, `advisory`.

## Diagnosis (v0.7)

### `perception_full_diagnosis`

Orchestrated QA pipeline: observe → console → network → accessibility + performance audits → visual → verification hints.

| Param | Type | Default |
|-------|------|---------|
| `session_id` | string | required |
| `url` | string | optional (current page if omitted) |
| `include_screenshot` | bool | `true` |
| `run_audits` | bool | `true` (a11y + performance only) |
| `timeout_s` | int | `120` |

**Returns:** `data.perception_report`, `data.agent_summary`, `scan_id`.

### `perception_debug_mode`

Observe + console + network without Lighthouse. Faster triage for runtime issues.

| Param | Type | Default |
|-------|------|---------|
| `session_id` | string | required |
| `url` | string | optional |
| `include_screenshot` | bool | `true` |

### `perception_audit_mode`

All four Lighthouse categories (accessibility, performance, seo, best-practices).

| Param | Type | Default |
|-------|------|---------|
| `session_id` | string | required |
| `url` | string | optional |
| `timeout_s` | int | `120` |

## Framework Intelligence (v1.0)

### `perception_detect_framework`

Detect frontend stack from `package.json`, lockfiles, configs, and folder structure. No browser session required.

| Param | Type | Default |
|-------|------|---------|
| `repo_root` | string | `sandbox/` |

**Returns:** `data.metadata` (`framework`, `framework_version`, `primary_package`, `build_tool`, `package_manager`, `language`, `is_monorepo`, `rendering_mode`, `router_mode`, `config_files`, `project_structure`).

### `perception_framework_docs`

Detect project → fetch version-aware framework docs on demand (Grounded Docs) → return normalized docs for one topic.

| Param | Type | Default |
|-------|------|---------|
| `repo_root` | string | `sandbox/` |
| `topic` | string | **required** (single concept) |
| `use_cache` | bool | `true` |

**Returns:** `data.framework_knowledge` (`metadata`, `content`, `summary`, `provider`, `library_id`, `cached`).

**Env:** `GROUNDED_DOCS_CLI`, `GROUNDED_DOCS_STORE_PATH`, `FRAMEWORK_DOCS_CACHE_PATH` (optional). Requires Node.js 22+ (`npx`).

## Component Intelligence (Phase 1)

### `perception_plan_component_search`

Build a deterministic search plan from a natural-language query. No provider calls.

| Param | Type | Default |
|-------|------|---------|
| `query` | string | **required** (e.g. `Modern glass dashboard navbar`) |

**Returns:** `data.search_plan` (`primary_intent`, `planned_queries`, `suggested_registries`, parsed fields). Host agent may refine before searching.

### `perception_search_components`

Parse query, build or accept a search plan, run multi-pass parallel provider search, merge duplicates, and return normalized candidates with session metadata.

| Param | Type | Default |
|-------|------|---------|
| `query` | string | **required** (e.g. `glassmorphism pricing section`, `minimal dark login form`) |
| `search_plan` | object | optional host-agent plan override |

**Returns:** `data.component_search` (`query`, `candidates`, `search_plan`, `search_session`, `providers_queried`, `total`). Each candidate includes `provider`, `name`, `category`, `install_method`, `relevance_score`, and merge metadata (`matched_query`, `search_pass`).

**Note:** Phase 1 merges provider-local scores only — Design Sense / Consistency ranking runs in `perception_select_component_foundation`.

### `perception_select_component_foundation`

Search + parallel cross-module guidance → choose best **foundation** (not perfect component).

| Param | Type | Default |
|-------|------|---------|
| `query` | string | **required** |
| `repo_root` | string | project root |
| `search_plan` | object | optional |
| `max_candidates` | integer | 12 |

**Returns:** `data.foundation_selection` (`chosen`, `guidance` per module, `runner_ups`, `rationale`).

### `perception_integrate_component`

Full pipeline: search or `candidate_id` → select → integrate → validate → repair loop (scaffold phases return `degraded`).

| Param | Type | Default |
|-------|------|---------|
| `query` | string | required if no `candidate_id` |
| `candidate_id` | string | skip search |
| `repo_root` | string | project root |
| `preview_url` | string | for browser validation |
| `max_repair_attempts` | integer | 3 |

**Returns:** `data.integration_result` (`status`, `selection`, `integration`, `validation`, `repair_attempts`).

## Resources

| URI | Content |
|-----|---------|
| `perception://agent-guide` | AGENT_GUIDE.md |
| `perception://eval/validation-form` | Eval scenario |
| `perception://scan/{id}/report.json` | Full observation (+ embedded `perception_report` when present) |
| `perception://scan/{id}/diagnosis.json` | Structured `PerceptionReport` |
| `perception://scan/{id}/diagnosis.md` | Human-readable diagnosis markdown |
| `perception://scan/{id}/screenshot.png` | Raw PNG |
| `perception://scan/{id}/screenshot-annotated.png` | Annotated PNG |
| `perception://scan/{id}/screenshot-crop.png` | Element crop |
| `perception://scan/{id}/network.har` | HAR 1.2 network trace |

## Install & run

```bash
pip install frontend-perception-engine   # or frontend-mcp
uvx --from frontend-mcp frontend-mcp
```

Cursor MCP:

```json
{
  "mcpServers": {
    "frontend-perception": {
      "command": "uvx",
      "args": ["--from", "frontend-mcp", "frontend-mcp"]
    }
  }
}
```
