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

Criteria: `url_contains`, `text_contains`, `js_assertions`, optional `section_id`.

Pass condition: **`data.verified=true`** (top-level `ok` is transport only).

On failure: `failure_scan_id`, inline annotated screenshot, `verified=false`.

For visual drafts, claim-done also requires section checklist + Ship Council when
`implementation_gate` sets those flags — see AGENT_GUIDE §19.

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

## Code context (deprecated)

### `perception_code_context`

**Deprecated.** Use Resolver Intelligence tools instead (`perception://resolver-guide`).

| Param | Default |
|-------|---------|
| `repo_root` | sandbox/ |
| `query_type` | `stats` |
| `query_kwargs` | {} |

Returns `degraded: ["use_perception_resolve_route"]`.

## Resolver Intelligence

Read `perception://resolver-guide` before calling these tools. All return `data.resolution` or `data.validation`.

**Always pass `repo_root`** (frontend app root with `package.json`).

### `perception_resolve_route`

Map route path → component file via static router config. Target &lt;200ms.

| Param | Required |
|-------|----------|
| `repo_root` | recommended |
| `path` | yes |

### `perception_validate_route_claim`

| Param | Required |
|-------|----------|
| `repo_root` | recommended |
| `claim.route`, `claim.file`, `claim.component.name` | claim object |

### `perception_resolve_component`

Component name → file (`components.json` + folder conventions).

| Param | Required |
|-------|----------|
| `name` | yes |

### `perception_validate_component_claim`

Validate component file/export claim.

### `perception_resolve_design_token`

CSS variables, tailwind config, DTCG JSON.

| Param | Required |
|-------|----------|
| `token` | yes |

### `perception_resolve_state_owner`

| Param | Notes |
|-------|-------|
| `key` | state field name |
| `store_name` | e.g. Cart, Auth |

### `perception_resolve_api_endpoint`

| Param | Required |
|-------|----------|
| `path` | yes |
| `method` | optional |

### `perception_resolve_layout`

| Param | Notes |
|-------|-------|
| `snapshot_id` or `scan_id` | design snapshot source |
| `region` | optional filter |

### `perception_correlate_live`

| Param | Required |
|-------|----------|
| `scan_id` | yes |
| `resolution` or `claim` | for DOM cross-check |

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

**Deprecated for agent hot paths** — heavy Grounded Docs fetch (Node.js 22+). Prefer host Context7 / IDE docs; use `perception_detect_framework` for stack metadata only.

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

## Inspiration Intelligence

Read MCP resource `perception://inspiration-guide` before calling these tools.

### `perception_inspiration_discover`

Ranked discovery across gallery providers (Dribbble → Land-book) with early stop. Fast — no capture or blobs.

| Param | Type | Default |
|-------|------|---------|
| `query` | string | **required** (e.g. `saas landing page`) |
| `max_candidates` | integer | 12 |
| `provider_preference` | string | optional provider id |

**Returns:** `data.inspiration_discovery` (candidates, search_plan, degraded). `agent_summary.top_hits` has url + preview_ref.

### `perception_inspiration_collect`

Full URL-first collection with optional ephemeral medium JPEG blobs for agent vision. Uses headed browser where required.

| Param | Type | Default |
|-------|------|---------|
| `query` | string | **required** |
| `per_provider` | integer | 4 |
| `provider_ids` | string[] | optional subset |
| `output_dir` | string | optional manifest path |
| `materialize_blobs` | bool | `true` |
| `blob_session_id` | string | reuse session |
| `download_images` | bool | `false` (permanent download) |

**Returns:** `data.inspiration_collection` manifest with `hits[]` (`agent_view_url`, `inspiration_blob`, `blob_session_id`).

### `perception_inspiration_session_end`

Delete ephemeral blobs when design work is complete.

| Param | Type | Default |
|-------|------|---------|
| `session_id` | string | blob session id from collect |
| `cleanup_expired` | bool | `false` — set true to TTL-clean all expired sessions |

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

## Figma Intelligence

Read `perception://figma-guide` before calling. Connection + coordination over southleft/figma-console-mcp — not design critique.

### `perception_figma_status`

Module phase, connection state, session, console health.

**Returns:** `data.figma_status`, `data.health`.

### `perception_figma_connect`

Connect user's Figma account with Personal Access Token (stored locally).

| Param | Type | Default |
|-------|------|---------|
| `pat` | string | required for connect |
| `action` | `connect` \| `status` \| `disconnect` | `connect` |
| `account_hint` | string | optional label |

**Flow:** User provides PAT once → validate → store → never ask again unless invalid.

### `perception_figma_context`

Normalized design context for active session.

| Param | Type | Default |
|-------|------|---------|
| `file_url` | string | Figma file/design URL |
| `file_key` | string | file key |
| `page_id` | string | active page |
| `frame_id` | string | active frame |
| `selection_node_ids` | string[] | selection override |
| `refresh` | boolean | `false` — bypass cache |

**Returns:** `data.figma_context` (`file`, `pages`, `components`, `variables`, `styles`, `tokens`, `selection`).

## SEO Intelligence

Read `perception://seo-guide` before calling. Orchestration layer — not Ahrefs/Semrush.

### `perception_seo_status`

Module phase, provider catalog, integration health, knowledge graph summary.

**Returns:** `data.seo_status` (`phase`, `providers_live`, `integrations`, `graph`, `do_not_build`).

### `perception_seo_connect`

Register a website (default) or run on-demand OAuth when provider data is needed.

| Param | Type | Default |
|-------|------|---------|
| `website_url` | string | required |
| `provider` | `google` \| `bing` | — (required for `connect_bing`) |
| `action` | `setup` \| `connect_google` \| `connect_bing` \| `connect` \| `status` \| `refresh_discovery` | `setup` |
| `interactive` | boolean | `true` (browser flow) |
| `code` | string | automation override only |
| `api_key` | string | Bing fallback when OAuth client not configured |

**Setup:** `website_url` only — no OAuth.

**On-demand OAuth:** `action=connect_google` or `connect_bing` → browser opens → sign-in → localhost callback on port 8787 → tokens stored.

### `perception_seo_audit_start`

Start SEO audit. **Preferred for agents.**

| Param | Type | Default |
|-------|------|---------|
| `website_url` | string | required |
| `mode` | string | `development` |
| `scan_id` | string | required for development |
| `repo_root` | string | optional |
| `budget_s` | number | `5.0` (development only) |

**Development (default):** synchronous inline result — `data.status: "completed"`, `data.instant: true`, `data.seo_audit` payload. No polling. Browser + AI Visibility only (requires `scan_id`).

**Professional:** returns `data.audit_job_id`, `data.poll_tool`, `data.poll_interval_ms` — poll with `perception_seo_audit_poll`.

### `perception_seo_audit_poll`

Poll background audit job.

| Param | Required |
|-------|----------|
| `audit_job_id` | yes |

**Returns:** `data.seo_audit_job` (status, progress, partial evidence).

### `perception_seo_audit_cancel`

| Param | Required |
|-------|----------|
| `audit_job_id` | yes |

### `perception_seo_audit`

**Legacy — blocks MCP server.** Use `perception_seo_audit_start` + `perception_seo_audit_poll` instead.

| Param | Type | Default |
|-------|------|---------|
| `website_url` | string | required |
| `mode` | string | auto — `development` or `professional` |
| `property_url` | string | advanced GSC override |
| `ga4_property_id` | string | advanced GA4 override |
| `bing_site_url` | string | advanced Bing override |
| `scan_id` | string | Browser Intelligence scan |
| `repo_root` | string | |
| `providers` | string[] | subset of provider ids |
| `intents` | string[] | capability ids |
| `include_cross_analysis` | boolean | true |
| `include_recommendations` | boolean | true |

**Returns:** `data.seo_audit` (`evidence`, `recommendations`, `reasoning_context`, `connections`, `degraded`, `graph_summary`, `verification`).

### `perception_seo_verify`

Re-audit and compare against graph baseline to close recommendation verification items.

| Param | Type | Default |
|-------|------|---------|
| `website_url` | string | required |
| `recommendation_ids` | string[] | all from graph if omitted |
| `scan_id` | string | Browser scan for rendering re-check |

**Returns:** `data.seo_verify` (`verification` with `passed_count`, `failed_count`, `items`).

## Resources

| URI | Content |
|-----|---------|
| `perception://agent-guide` | AGENT_GUIDE.md — main playbooks |
| `perception://resolver-guide` | Resolver Intelligence — resolve_* tools |
| `perception://seo-guide` | SEO_AGENT_GUIDE.md — Development inline vs Professional poll |
| `perception://inspiration-guide` | Inspiration Intelligence |
| `perception://resource-guide` | Resource Intelligence |
| `perception://figma-guide` | Figma Intelligence |
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
