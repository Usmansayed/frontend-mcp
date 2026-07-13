"""MCP tool definitions (schemas + playbook descriptions)."""
from __future__ import annotations

from typing import Any


def perception_tools(mcp_types: Any) -> list[Any]:
    """Return Tool list; mcp_types is mcp.types when MCP is installed."""
    T = mcp_types.Tool
    return [
        T(
            name="perception_health",
            description=(
                "Playbook: session bootstrap (AGENT_GUIDE §1). Check dev server reachable before any work. "
                "Returns reachable + HTTP status. If false, ask user to start the app."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Base URL, e.g. http://localhost:5173"},
                },
            },
        ),
        T(
            name="perception_session_start",
            description=(
                "Playbook: session bootstrap (AGENT_GUIDE §1). Start browser session. "
                "Call once per task; reuse session_id for all following tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "base_url": {"type": "string", "description": "App base URL"},
                    "headless": {"type": "boolean", "default": True},
                    "viewport": {
                        "type": "object",
                        "properties": {
                            "width": {"type": "integer", "default": 1920},
                            "height": {"type": "integer", "default": 1080},
                        },
                    },
                },
            },
        ),
        T(
            name="perception_session_end",
            description="Playbook: teardown (AGENT_GUIDE §1). End browser session and release resources.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_navigate",
            description=(
                "Playbook: NAVIGATE without full observe (AGENT_GUIDE §5). Preflight navigate only; "
                "pair with perception_observe when you need DOM/a11y/screenshot."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string", "description": "Path or absolute URL"},
                },
                "required": ["session_id", "url"],
            },
        ),
        T(
            name="perception_navigate_and_observe",
            description=(
                "Playbook: OBSERVE phase (AGENT_GUIDE §0, §2–§3). Navigate and return DOM, a11y, "
                "dev insights, visual_insights, and INLINE annotated screenshots in the tool response. "
                "Images are attached automatically — do not skip looking at them. Save scan_id for diff."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string", "description": "Path or absolute URL"},
                    "include_screenshot": {
                        "type": "boolean",
                        "default": True,
                        "description": "Capture screenshot(s). Set false to skip all images.",
                    },
                    "screenshot_mode": {
                        "type": "string",
                        "enum": ["viewport", "full", "element"],
                        "default": "viewport",
                        "description": "viewport=visible area; full=scrollable page; element=crop to selector",
                    },
                    "screenshot_selector": {
                        "type": "string",
                        "description": "CSS selector when screenshot_mode=element",
                    },
                    "annotate_screenshot": {
                        "type": "boolean",
                        "default": True,
                        "description": "Overlay interactive boxes and blocking issues on screenshot",
                    },
                    "detail": {
                        "type": "string",
                        "enum": ["full", "summary_only"],
                        "default": "full",
                        "description": "summary_only omits DOM payload but still returns visual block + inline images",
                    },
                    "budget": {
                        "type": "object",
                        "properties": {
                            "max_a11y_chars": {"type": "integer"},
                            "max_dom_chars": {"type": "integer"},
                            "max_list_items": {"type": "integer"},
                        },
                    },
                },
                "required": ["session_id", "url"],
            },
        ),
        T(
            name="perception_observe",
            description=(
                "Playbook: OBSERVE current page (AGENT_GUIDE §2). Snapshot with INLINE annotated screenshots. "
                "Use after in-page actions. visual_insights includes layout issues (overflow, overlaps)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "include_screenshot": {"type": "boolean", "default": True},
                    "screenshot_mode": {
                        "type": "string",
                        "enum": ["viewport", "full", "element"],
                        "default": "viewport",
                    },
                    "screenshot_selector": {"type": "string"},
                    "annotate_screenshot": {"type": "boolean", "default": True},
                    "detail": {
                        "type": "string",
                        "enum": ["full", "summary_only"],
                        "default": "full",
                        "description": "summary_only omits DOM but keeps visual block + inline images",
                    },
                    "budget": {
                        "type": "object",
                        "properties": {
                            "max_a11y_chars": {"type": "integer"},
                            "max_dom_chars": {"type": "integer"},
                            "max_list_items": {"type": "integer"},
                        },
                    },
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_execute_script",
            description=(
                "Playbook: ACT phase (AGENT_GUIDE §0, §4). Execute agent-authored JS IIFE in the page. "
                "Use for custom interactions (e.g. checkbox toggle). Always follow with perception_verify."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "script": {"type": "string", "description": "JavaScript IIFE to run in page context"},
                    "capture_insights_during": {"type": "boolean", "default": True},
                },
                "required": ["session_id", "script"],
            },
        ),
        T(
            name="perception_execute_actions",
            description=(
                "Playbook: ACT — deterministic clicks/fills (AGENT_GUIDE §4 forms, §6 flows). "
                "Actions: click_button, click_link, set_input. Follow with perception_verify."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["click_button", "click_link", "set_input"],
                                },
                                "text": {"type": "string"},
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["type"],
                        },
                    },
                    "capture_insights_during": {"type": "boolean", "default": True},
                },
                "required": ["session_id", "actions"],
            },
        ),
        T(
            name="perception_verify",
            description=(
                "Playbook: VERIFY phase (AGENT_GUIDE §0, §7). Assert URL/text/JS criteria. "
                "On failure automatically captures annotated screenshot inline with failure_scan_id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "criteria": {
                        "type": "object",
                        "properties": {
                            "url_contains": {"type": "array", "items": {"type": "string"}},
                            "url_not_contains": {"type": "array", "items": {"type": "string"}},
                            "url_regex": {"type": "string"},
                            "text_contains": {"type": "array", "items": {"type": "string"}},
                            "text_absent": {"type": "array", "items": {"type": "string"}},
                            "js_assertions": {"type": "array", "items": {"type": "string"}},
                            "accept_urls": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "required": ["session_id", "criteria"],
            },
        ),
        T(
            name="perception_diff",
            description=(
                "Playbook: VERIFY / regression (AGENT_GUIDE §7). Compare scan_ids — text diff plus "
                "INLINE side-by-side and heatmap images when screenshots exist."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scan_id_before": {"type": "string"},
                    "scan_id_after": {"type": "string"},
                },
                "required": ["scan_id_before", "scan_id_after"],
            },
        ),
        T(
            name="perception_auth_gate",
            description=(
                "Playbook: safety stop (AGENT_GUIDE §5, §12). Detect login/MFA/CAPTCHA surfaces. "
                "If requires_human is true, stop automation and ask the user."
            ),
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_probe_form",
            description=(
                "Playbook: forms (AGENT_GUIDE §4). Run before filling — invalid submit rules, then valid submit probe."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "form": {"type": "string", "default": "validation", "description": "Form preset name"},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_probe_guards",
            description=(
                "Playbook: route guards (AGENT_GUIDE §5). mode=maze runs sandbox guard suite; "
                "mode=routes probes custom route list."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "mode": {"type": "string", "enum": ["maze", "routes"], "default": "maze"},
                    "routes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "route": {"type": "string"},
                                "expected_redirect": {"type": "string"},
                                "requires_auth": {"type": "boolean"},
                                "requires_role": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_state_save",
            description="Playbook: stateful flows (AGENT_GUIDE §5). Snapshot cookies/storage/URL for later restore.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "state_id": {"type": "string"},
                },
                "required": ["session_id", "state_id"],
            },
        ),
        T(
            name="perception_state_restore",
            description="Playbook: stateful flows (AGENT_GUIDE §5). Restore cookies/storage/URL from state_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "state_id": {"type": "string"},
                },
                "required": ["session_id", "state_id"],
            },
        ),
        T(
            name="perception_state_list",
            description="Playbook: stateful flows (AGENT_GUIDE §5). List saved state_ids for the session.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_flow_describe",
            description=(
                "Playbook: multi-step flows (AGENT_GUIDE §6). Omit flow_name to list flows; "
                "set flow_name for checkpoint graph and success criteria."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_name": {"type": "string", "description": "e.g. validation-form, shop-order"},
                },
            },
        ),
        T(
            name="perception_code_context",
            description=(
                "DEPRECATED — prefer perception_resolve_route / perception_validate_route_claim. "
                "Playbook: code ↔ UI correlation (AGENT_GUIDE §10)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string", "description": "Path to frontend repo (default: sandbox/)"},
                    "enabled": {"type": "boolean", "default": True},
                    "query_type": {"type": "string", "default": "stats"},
                    "query_kwargs": {"type": "object"},
                },
            },
        ),
        T(
            name="perception_resolve_route",
            description=(
                "Resolver Intelligence. Route path → component file (<200ms). "
                "Read perception://resolver-guide. AGENT_GUIDE §10."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "path": {"type": "string", "description": "Route path e.g. /forms/validation"},
                    "route": {"type": "string", "description": "Alias for path"},
                },
                "required": ["path"],
            },
        ),
        T(
            name="perception_validate_route_claim",
            description=(
                "Resolver Intelligence. Validate route→file→component claim. "
                "Read perception://resolver-guide."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "claim": {
                        "type": "object",
                        "properties": {
                            "route": {"type": "string"},
                            "file": {"type": "string"},
                            "component": {"type": "object", "properties": {"name": {"type": "string"}}},
                        },
                    },
                },
                "required": ["claim"],
            },
        ),
        T(
            name="perception_resolve_component",
            description="Resolver Intelligence. Component name → file. Read perception://resolver-guide.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["name"],
            },
        ),
        T(
            name="perception_validate_component_claim",
            description="Resolver Intelligence. Validate component file claim. Read perception://resolver-guide.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "claim": {"type": "object"},
                },
                "required": ["claim"],
            },
        ),
        T(
            name="perception_resolve_design_token",
            description="Resolver Intelligence. Design token → CSS/tailwind/DTCG. Read perception://resolver-guide.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "token": {"type": "string"},
                },
                "required": ["token"],
            },
        ),
        T(
            name="perception_resolve_state_owner",
            description="Resolver Intelligence. State key/store → owner file. Read perception://resolver-guide.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "key": {"type": "string"},
                    "store_name": {"type": "string"},
                },
            },
        ),
        T(
            name="perception_resolve_api_endpoint",
            description="Resolver Intelligence. API path → handler file. Read perception://resolver-guide.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "path": {"type": "string"},
                    "method": {"type": "string"},
                },
                "required": ["path"],
            },
        ),
        T(
            name="perception_resolve_layout",
            description="Resolver Intelligence. Layout regions from design snapshot. Read perception://resolver-guide.",
            inputSchema={
                "type": "object",
                "properties": {
                    "snapshot_id": {"type": "string"},
                    "scan_id": {"type": "string"},
                    "region": {"type": "string"},
                },
            },
        ),
        T(
            name="perception_correlate_live",
            description=(
                "Resolver Intelligence. Cross-check resolution/claim against scan DOM. "
                "Requires scan_id from observe. Read perception://resolver-guide."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scan_id": {"type": "string"},
                    "resolution": {"type": "object"},
                    "claim": {"type": "object"},
                },
                "required": ["scan_id"],
            },
        ),
        T(
            name="perception_console_get",
            description=(
                "Playbook: debugging (AGENT_GUIDE §3). Session console history from CDP — all levels "
                "(log/info/debug/warn/error/exception). Filter by levels, substring, since_index."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "levels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "e.g. error, warn, log, info, debug, exception",
                    },
                    "contains": {"type": "string", "description": "Substring filter (case-insensitive)"},
                    "since_index": {
                        "type": "integer",
                        "description": "Absolute session entry index — return entries at or after this index",
                    },
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_console_clear",
            description="Playbook: debugging. Wipe session console ring buffer.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_network_get",
            description=(
                "Playbook: debugging (AGENT_GUIDE §3). Session network history from CDP — "
                "requests, failures, slow/duplicate detection, optional response bodies."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "failed_only": {"type": "boolean", "default": False},
                    "api_group": {"type": "string", "description": "Filter by /api/{group}/ prefix"},
                    "contains": {"type": "string", "description": "URL substring filter"},
                    "status_min": {"type": "integer"},
                    "status_max": {"type": "integer"},
                    "since_index": {"type": "integer"},
                    "limit": {"type": "integer", "default": 50},
                    "include_bodies": {"type": "boolean", "default": False},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_network_clear",
            description="Playbook: debugging. Wipe session network ring buffer.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_audit_accessibility",
            description=(
                "Playbook: quality (AGENT_GUIDE §3). Run Lighthouse accessibility audit on current page "
                "or optional url. Requires Node.js (npx lighthouse). Returns score, warnings, blocking."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string", "description": "Optional path or absolute URL"},
                    "timeout_s": {"type": "integer", "default": 120},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_audit_performance",
            description="Lighthouse performance audit (Core Web Vitals metrics). Requires Node.js.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string"},
                    "timeout_s": {"type": "integer", "default": 120},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_audit_seo",
            description="Lighthouse SEO audit. Requires Node.js.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string"},
                    "timeout_s": {"type": "integer", "default": 120},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_audit_best_practices",
            description="Lighthouse best-practices audit. Requires Node.js.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string"},
                    "timeout_s": {"type": "integer", "default": 120},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_full_diagnosis",
            description=(
                "Playbook: comprehensive QA (AGENT_GUIDE §3). Orchestrates observe + console + network "
                "+ accessibility + performance audits + visual insights into one PerceptionReport. "
                "Set run_audits=false to skip Lighthouse. Returns scan_id and perception_report."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string", "description": "Optional path or absolute URL"},
                    "include_screenshot": {"type": "boolean", "default": True},
                    "run_audits": {"type": "boolean", "default": True},
                    "timeout_s": {"type": "integer", "default": 120},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_debug_mode",
            description=(
                "Playbook: debugging (AGENT_GUIDE §3). Observe + console + network report without "
                "Lighthouse. Faster than full_diagnosis when triaging runtime issues."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string"},
                    "include_screenshot": {"type": "boolean", "default": True},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_audit_mode",
            description=(
                "Run all four Lighthouse categories (accessibility, performance, seo, best-practices) "
                "on current page or optional url. Requires Node.js."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "url": {"type": "string"},
                    "timeout_s": {"type": "integer", "default": 120},
                },
                "required": ["session_id"],
            },
        ),
        T(
            name="perception_detect_framework",
            description=(
                "Framework Intelligence (v1). Detect frontend stack from package.json, lockfiles, "
                "configs, and folder structure. Returns framework, version, build tool, package manager, "
                "TypeScript/JavaScript, monorepo flag, and rendering/router hints."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {
                        "type": "string",
                        "description": "Project root with package.json (default: sandbox/)",
                    },
                },
            },
        ),
        T(
            name="perception_framework_docs",
            description=(
                "Framework Intelligence (v1). Detect project metadata, fetch version-aware framework "
                "documentation on demand via Grounded Docs, and return a normalized response. "
                "Requires Node.js 22+ (npx). Override with GROUNDED_DOCS_CLI / GROUNDED_DOCS_STORE_PATH."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string", "description": "Project root (default: sandbox/)"},
                    "topic": {
                        "type": "string",
                        "description": "One documentation topic, e.g. 'useEffect cleanup' or 'form validation'",
                    },
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": ["topic"],
            },
        ),
        T(
            name="perception_plan_component_search",
            description=(
                "Component Intelligence. Build a deterministic search plan from a natural-language "
                "query (primary intent, expanded terminology, style/theme hints, suggested registries, "
                "multi-pass queries). The host agent may refine this plan before searching. No provider "
                "calls — plan only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "e.g. 'Modern glass dashboard navbar'",
                    },
                },
                "required": ["query"],
            },
        ),
        T(
            name="perception_search_components",
            description=(
                "Component Intelligence. Parse query, build or accept a search plan, run multi-pass "
                "parallel provider search with provider-aware vocabulary, merge duplicates, and return "
                "normalized candidates with search session metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "e.g. 'glassmorphism pricing section' or 'minimal dark login form'",
                    },
                    "search_plan": {
                        "type": "object",
                        "description": "Optional host-agent search plan override",
                    },
                },
                "required": ["query"],
            },
        ),
        T(
            name="perception_select_component_foundation",
            description=(
                "Component Intelligence. Search, consult Framework/Codebase/Design Sense/Consistency "
                "guidance in parallel, and choose the best foundation component for the project — "
                "not the 'perfect' match, but the strongest starting point to adapt."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language component request"},
                    "repo_root": {"type": "string", "description": "Project root (default: sandbox/)"},
                    "search_plan": {"type": "object", "description": "Optional search plan override"},
                    "max_candidates": {"type": "integer", "default": 12},
                },
                "required": ["query"],
            },
        ),
        T(
            name="perception_integrate_component",
            description=(
                "Component Intelligence. Full orchestration: search (or candidate_id) → select foundation → "
                "documentation reader → dependency/compatibility resolution → install → adapt → "
                "browser validate → repair loop. Partial phases are scaffolded; returns structured status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Component request if not using candidate_id"},
                    "candidate_id": {"type": "string", "description": "Skip search; integrate this candidate"},
                    "repo_root": {"type": "string", "description": "Project root"},
                    "preview_url": {"type": "string", "description": "URL for post-install browser validation"},
                    "search_plan": {"type": "object"},
                    "max_repair_attempts": {"type": "integer", "default": 3},
                    "execute_install": {
                        "type": "boolean",
                        "default": False,
                        "description": "Run package/provider install commands (default: plan only)",
                    },
                    "execute_repairs": {
                        "type": "boolean",
                        "default": False,
                        "description": "Apply repair actions after validation failure (default: plan only)",
                    },
                },
            },
        ),
        T(
            name="perception_inspiration_discover",
            description=(
                "Inspiration Intelligence. Ranked discovery across Dribbble, Behance, One Page Love, "
                "Awwwards, SiteInspire, Godly, and Land-book with priority cascade and early stop. "
                "Returns URLs and scores — no capture. Read perception://inspiration-guide for per-site rules."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "e.g. 'saas landing page' or 'minimal fintech dashboard'",
                    },
                    "max_candidates": {"type": "integer", "default": 12},
                    "provider_preference": {
                        "type": "string",
                        "description": "Optional provider id to prefer (e.g. dribbble, behance)",
                    },
                },
                "required": ["query"],
            },
        ),
        T(
            name="perception_inspiration_collect",
            description=(
                "Inspiration Intelligence. Full URL-first collection with optional ephemeral medium JPEG "
                "blobs for agent vision. Returns manifest hits with agent_view_url and inspiration_blob. "
                "Uses headed browser where required (Dribbble WAF, Awwwards, Godly, Land-book). "
                "Read perception://inspiration-guide before calling."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Inspiration search query"},
                    "per_provider": {"type": "integer", "default": 4},
                    "provider_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Subset of provider ids to query",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional path to write manifest.json and per-hit metadata",
                    },
                    "materialize_blobs": {
                        "type": "boolean",
                        "default": True,
                        "description": "Create ephemeral medium JPEG blobs for vision",
                    },
                    "blob_session_id": {
                        "type": "string",
                        "description": "Reuse existing blob session id",
                    },
                    "download_images": {
                        "type": "boolean",
                        "default": False,
                        "description": "Permanently download preview images (separate from ephemeral blobs)",
                    },
                },
                "required": ["query"],
            },
        ),
        T(
            name="perception_inspiration_session_end",
            description=(
                "Inspiration Intelligence. Delete ephemeral inspiration blobs for a session when design "
                "work is complete. Pass cleanup_expired=true to remove TTL-expired sessions instead."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Blob session id from collect (e.g. insp_abc123)",
                    },
                    "cleanup_expired": {
                        "type": "boolean",
                        "default": False,
                        "description": "Remove all TTL-expired blob sessions",
                    },
                },
            },
        ),
        T(
            name="perception_resource_search",
            description=(
                "Resource Intelligence. Search commercial-safe creative assets. Icons use a consistent "
                "icon family (Lucide, Heroicons, etc.) by default — URLs + npm imports, no blobs. "
                "Read perception://resource-guide before calling."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "e.g. 'settings gear icon' or 'minimal user avatar'",
                    },
                    "max_results": {"type": "integer", "default": 12},
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional category filter: icon, avatar, font, photo, ...",
                    },
                    "provider_preference": {
                        "type": "string",
                        "description": "Optional provider id (overrides icon family routing)",
                    },
                    "icon_family": {
                        "type": "string",
                        "description": "Icon set family: lucide, heroicons, tabler-icons, phosphor-icons, remix-icon",
                    },
                    "icon_family_strict": {
                        "type": "boolean",
                        "default": True,
                        "description": "Search only inside icon_family before fallback",
                    },
                    "allow_family_fallback": {
                        "type": "boolean",
                        "default": True,
                        "description": "Broaden search when icon not found in family",
                    },
                    "persist_icon_family": {
                        "type": "boolean",
                        "default": False,
                        "description": "Save icon_family to .cache/resource_icon_family.json",
                    },
                    "commercial_required": {"type": "boolean", "default": True},
                    "attribution_ok": {"type": "boolean", "default": True},
                    "prefer_svg": {"type": "boolean", "default": True},
                },
                "required": ["query"],
            },
        ),
        T(
            name="perception_resource_preview",
            description=(
                "Resource Intelligence. Search + optional vision blobs. In-family icons skip blobs "
                "(use access_url). Blobs only for family miss + reference_preview_url fallback. "
                "Read perception://resource-guide before calling."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Resource search query"},
                    "max_results": {"type": "integer", "default": 12},
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "icon_family": {"type": "string"},
                    "icon_family_strict": {"type": "boolean", "default": True},
                    "allow_family_fallback": {"type": "boolean", "default": True},
                    "persist_icon_family": {"type": "boolean", "default": False},
                    "blob_fallback_only": {
                        "type": "boolean",
                        "default": True,
                        "description": "Skip blobs for in-family icons (default true)",
                    },
                    "reference_preview_url": {
                        "type": "string",
                        "description": "When family has no match — preview URL for vision/OCR blob",
                    },
                    "reference_image_path": {
                        "type": "string",
                        "description": "Local screenshot path when family has no match",
                    },
                    "provider_preference": {"type": "string"},
                    "asset_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Subset of resource_id values from search",
                    },
                    "materialize_blobs": {
                        "type": "boolean",
                        "default": True,
                        "description": "Create ephemeral medium JPEG blobs for vision",
                    },
                    "blob_session_id": {
                        "type": "string",
                        "description": "Reuse existing blob session id",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional path to write manifest.json",
                    },
                },
                "required": ["query"],
            },
        ),
        T(
            name="perception_resource_session_end",
            description=(
                "Resource Intelligence. Delete ephemeral resource preview blobs when asset work is complete. "
                "Pass cleanup_expired=true to remove TTL-expired sessions instead."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Blob session id from preview (e.g. res_abc123)",
                    },
                    "cleanup_expired": {
                        "type": "boolean",
                        "default": False,
                        "description": "Remove all TTL-expired blob sessions",
                    },
                },
            },
        ),
        T(
            name="perception_resource_icon_search",
            description="Resource Intelligence. Search icons in project icon family with verified imports.",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        T(
            name="perception_resource_font_search",
            description="Resource Intelligence. Search Fontsource npm font families with install guidance.",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        T(
            name="perception_resource_logo_search",
            description="Resource Intelligence. Search brand logos (theSVG / Simple Icons).",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        T(
            name="perception_resource_photo_search",
            description="Resource Intelligence. Search Pexels photos (PEXELS_API_KEY required).",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        T(
            name="perception_resource_avatar_search",
            description="Resource Intelligence. Search DiceBear avatars.",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        T(
            name="perception_resource_illustration_search",
            description="Resource Intelligence. Search Open Doodles and IRA Design illustrations.",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        T(
            name="perception_resource_pattern_search",
            description="Resource Intelligence. Search background patterns and textures (Hero Patterns and similar).",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        T(
            name="perception_resource_animation_search",
            description="Resource Intelligence. Search Lottie / motion animations for UI micro-interactions.",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        T(
            name="perception_resource_license_check",
            description="Resource Intelligence. Structured license check for a resource asset object.",
            inputSchema={
                "type": "object",
                "properties": {"asset": {"type": "object"}, "commercial_required": {"type": "boolean", "default": True}},
                "required": ["asset"],
            },
        ),
        T(
            name="perception_resource_observe_bridge",
            description=(
                "Resource Intelligence. Bridge perception_observe scan to icon search — family match or vision fallback."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scan_id": {"type": "string"},
                    "query": {"type": "string"},
                    "icon_family": {"type": "string"},
                    "repo_root": {"type": "string"},
                },
                "required": ["scan_id", "query"],
            },
        ),
        T(
            name="perception_seo_status",
            description=(
                "SEO Intelligence. Module phase, free-first provider catalog, knowledge graph summary. "
                "Read perception://seo-guide first. Not Ahrefs/Semrush — orchestration layer only."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        T(
            name="perception_seo_audit",
            description=(
                "SEO Intelligence. Default mode=development (no auth): Browser, Lighthouse, LibreCrawl. "
                "mode=professional adds GSC/GA4 when user requests live search optimization."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "website_url": {"type": "string", "description": "Site to audit (required)"},
                    "mode": {
                        "type": "string",
                        "enum": ["development", "professional"],
                        "description": "Omit for auto (development default; professional when GSC/GA4 intents requested)",
                    },
                    "property_url": {
                        "type": "string",
                        "description": "Advanced: GSC property override if auto-discovery failed",
                    },
                    "ga4_property_id": {
                        "type": "string",
                        "description": "Advanced: GA4 property override if auto-discovery failed",
                    },
                    "bing_site_url": {
                        "type": "string",
                        "description": "Advanced: Bing site override if auto-discovery failed",
                    },
                    "scan_id": {"type": "string", "description": "Browser Intelligence scan for rendering evidence"},
                    "repo_root": {"type": "string", "description": "Frontend repo root for codebase_hints and browser_code_links (Sprint 2)"},
                    "providers": {"type": "array", "items": {"type": "string"}},
                    "intents": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Capabilities e.g. keyword_research, technical_crawl, core_web_vitals",
                    },
                    "include_cross_analysis": {"type": "boolean", "default": True},
                    "include_recommendations": {"type": "boolean", "default": True},
                    "include_ai_visibility": {
                        "type": "boolean",
                        "default": True,
                        "description": "Run the AI Visibility layer (derived analysis over SEO evidence). Set false to skip.",
                    },
                    "ai_reasoning": {
                        "type": "boolean",
                        "description": "Use host LLM over reasoning_units (auto when Bedrock creds available; false forces deterministic fallback)",
                    },
                },
                "required": ["website_url"],
            },
        ),
        T(
            name="perception_seo_audit_start",
            description=(
                "SEO Intelligence (async). Enqueue audit → audit_job_id (<500ms). "
                "Poll perception_seo_audit_poll. Read perception://seo-guide. AGENT_GUIDE §15."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "website_url": {"type": "string", "description": "Site to audit (required)"},
                    "mode": {"type": "string", "enum": ["development", "professional"]},
                    "property_url": {"type": "string"},
                    "ga4_property_id": {"type": "string"},
                    "bing_site_url": {"type": "string"},
                    "scan_id": {"type": "string"},
                    "repo_root": {"type": "string"},
                    "providers": {"type": "array", "items": {"type": "string"}},
                    "intents": {"type": "array", "items": {"type": "string"}},
                    "include_cross_analysis": {"type": "boolean", "default": True},
                    "include_recommendations": {"type": "boolean", "default": True},
                    "include_ai_visibility": {"type": "boolean", "default": True},
                    "ai_reasoning": {"type": "boolean"},
                },
                "required": ["website_url"],
            },
        ),
        T(
            name="perception_seo_audit_poll",
            description=(
                "SEO Intelligence (async). Poll background audit job for status, progress, and evidence deltas."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "audit_job_id": {"type": "string"},
                    "since_evidence_seq": {
                        "type": "integer",
                        "description": "Return evidence_delta entries after this sequence number",
                    },
                },
                "required": ["audit_job_id"],
            },
        ),
        T(
            name="perception_seo_audit_cancel",
            description="SEO Intelligence (async). Cancel a background audit job by audit_job_id.",
            inputSchema={
                "type": "object",
                "properties": {"audit_job_id": {"type": "string"}},
                "required": ["audit_job_id"],
            },
        ),
        T(
            name="perception_seo_connect",
            description=(
                "SEO Intelligence setup and on-demand OAuth. Default action=setup registers website_url only. "
                "Use action=connect_google or connect_bing when user requests provider-specific analysis."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "website_url": {"type": "string", "description": "Website URL"},
                    "provider": {
                        "type": "string",
                        "enum": ["google", "bing"],
                        "description": "Required for connect_bing; use with action=connect for Google",
                    },
                    "action": {
                        "type": "string",
                        "enum": [
                            "status",
                            "setup",
                            "connect",
                            "connect_google",
                            "connect_bing",
                            "refresh_discovery",
                        ],
                        "default": "setup",
                    },
                    "interactive": {
                        "type": "boolean",
                        "default": True,
                        "description": "When true, opens browser and waits for localhost OAuth callback",
                    },
                    "code": {
                        "type": "string",
                        "description": "Manual OAuth code override (automation/testing only)",
                    },
                    "api_key": {
                        "type": "string",
                        "description": "Bing API key fallback when Bing OAuth client not configured",
                    },
                },
            },
        ),
        T(
            name="perception_seo_query",
            description=(
                "Query the SEO knowledge graph — page issues, audit diff, traffic signals. "
                "Omit query_id to list available queries. Run perception_seo_audit first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query_id": {
                        "type": "string",
                        "enum": [
                            "graph.summary",
                            "page.issues",
                            "audit.latest",
                            "audit.diff",
                            "site.traffic_signals",
                        ],
                    },
                    "page_url": {"type": "string", "description": "For page.issues"},
                    "audit_id": {"type": "string", "description": "For audit.diff (default: latest)"},
                    "params": {"type": "object", "description": "Alternative param bag"},
                },
            },
        ),
        T(
            name="perception_seo_verify",
            description=(
                "SEO Intelligence verification loop. Re-audit site and compare against graph baseline recommendations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "website_url": {"type": "string"},
                    "property_url": {"type": "string"},
                    "ga4_property_id": {"type": "string"},
                    "scan_id": {"type": "string"},
                    "recommendation_ids": {"type": "array", "items": {"type": "string"}},
                    "providers": {"type": "array", "items": {"type": "string"}},
                    "intents": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["website_url"],
            },
        ),
        T(
            name="perception_figma_status",
            description=(
                "Figma Intelligence. Connection state, session, health of southleft/figma-console-mcp. "
                "Read perception://figma-guide first. Connection + coordination only — not design critique."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        T(
            name="perception_figma_connect",
            description=(
                "Figma Intelligence. Connect user's Figma account with Personal Access Token (stored locally). "
                "action=status to check connection; action=disconnect to clear token."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pat": {"type": "string", "description": "Figma Personal Access Token"},
                    "figma_pat": {"type": "string", "description": "Alias for pat"},
                    "action": {
                        "type": "string",
                        "enum": ["connect", "status", "disconnect"],
                        "description": "Default connect — validates and stores PAT",
                    },
                    "account_hint": {"type": "string", "description": "Optional label for stored token"},
                },
            },
        ),
        T(
            name="perception_figma_context",
            description=(
                "Figma Intelligence. Normalized design context — file, pages, frames, components, "
                "variables, styles, tokens, selection. Optionally set file_url/file_key and refresh."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_key": {"type": "string"},
                    "file_url": {"type": "string", "description": "Figma file or design URL"},
                    "file_name": {"type": "string"},
                    "page_id": {"type": "string"},
                    "frame_id": {"type": "string"},
                    "selection_node_ids": {"type": "array", "items": {"type": "string"}},
                    "refresh": {"type": "boolean", "default": False},
                },
            },
        ),
        T(
            name="perception_build_design_snapshot",
            description=(
                "Design pipeline: build structured DesignSnapshot from scan_id or session. "
                "Run after perception_observe. Returns snapshot_id + typography/color/layout reports. "
                "Never critiques — extraction only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "scan_id": {"type": "string", "description": "Preferred — from perception_observe"},
                    "snapshot_id": {"type": "string", "description": "Return existing snapshot"},
                    "use_designlang": {
                        "type": "boolean",
                        "default": False,
                        "description": "Augment with designlang CLI when DESIGNLANG_ENABLED=1",
                    },
                },
            },
        ),
        T(
            name="perception_design_review",
            description=(
                "Design Sense Intelligence: full design review from snapshot. "
                "Pass scan_id from observe or snapshot_id. Agent must NOT build ReviewRequest manually. "
                "Returns consolidated findings, blocking issues, reference comparisons, recommendations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "scan_id": {"type": "string"},
                    "snapshot_id": {"type": "string"},
                    "user_task": {"type": "string", "description": "What the user is trying to accomplish"},
                    "scope": {
                        "type": "string",
                        "enum": ["page", "flow", "feature", "component", "region"],
                        "default": "page",
                    },
                    "compare_references": {
                        "type": "boolean",
                        "default": True,
                        "description": "Compare against reference registry (Stripe, Linear, etc.)",
                    },
                    "use_designlang": {"type": "boolean", "default": False},
                },
            },
        ),
        T(
            name="perception_consistency_review",
            description=(
                "Consistency Intelligence: refresh Project Design Graph from snapshot + codebase/tokens, "
                "then batch-audit interactive elements against learned standards."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "scan_id": {"type": "string"},
                    "snapshot_id": {"type": "string"},
                    "repo_root": {"type": "string"},
                    "project_id": {"type": "string"},
                    "use_designlang": {"type": "boolean", "default": False},
                },
            },
        ),
        T(
            name="perception_consistency_audit",
            description=(
                "Consistency Intelligence: batch audit snapshot elements against populated Project Design Graph. "
                "Run perception_design_graph_refresh first if graph is empty."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "scan_id": {"type": "string"},
                    "snapshot_id": {"type": "string"},
                    "design_snapshot": {"type": "object"},
                    "repo_root": {"type": "string"},
                    "project_id": {"type": "string"},
                    "max_elements": {"type": "number", "default": 40},
                },
            },
        ),
        T(
            name="perception_design_knowledge_query",
            description=(
                "Consistency Intelligence Knowledge API: query the Project Design Graph. "
                "Returns evidence, standards, confidence, exceptions, alternatives, and recommendations. "
                "Use query_id from the catalog (e.g. graph.summary, standard.for_context, component.variants)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query_id": {"type": "string", "description": "Registered query id"},
                    "params": {"type": "object", "description": "Query parameters"},
                    "project_id": {"type": "string", "default": "default"},
                    "repo_root": {"type": "string", "description": "Optional repo root for graph persistence"},
                },
                "required": ["query_id"],
            },
        ),
        T(
            name="perception_design_graph_summary",
            description=(
                "Consistency Intelligence: high-level Project Design Graph overview for agent bootstrap. "
                "Returns KnowledgeResponse with stats, standards, and exceptions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "default": "default"},
                    "repo_root": {"type": "string"},
                },
            },
        ),
        T(
            name="perception_design_graph_refresh",
            description=(
                "Consistency Intelligence: run Discovery Pipeline to ingest knowledge from enabled sources "
                "(snapshot, codebase, tokens) into the Project Design Graph. "
                "Pass repo_root for codebase/tokens scan; pass session_id, scan_id, snapshot_id, or design_snapshot "
                "for browser snapshot ingestion."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "default": "default"},
                    "repo_root": {"type": "string", "description": "Repo root for codebase and token sources"},
                    "session_id": {"type": "string"},
                    "scan_id": {"type": "string"},
                    "snapshot_id": {"type": "string"},
                    "design_snapshot": {"type": "object", "description": "Inline DesignSnapshot dict"},
                    "enabled_sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Subset of: snapshot, codebase, tokens",
                    },
                },
            },
        ),
        T(
            name="perception_consistency_assess",
            description=(
                "Consistency Intelligence (Phase 3): assess element against Project Design Graph standards. "
                "Thin consumer — queries graph only, never owns rules. "
                "Pass selector and actual computed styles (e.g. padding, border-radius)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "actual": {
                        "type": "object",
                        "description": "Property → value map from observation",
                    },
                    "context": {"type": "string", "description": "UI context override (default: inferred from selector)"},
                    "properties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "project_id": {"type": "string", "default": "default"},
                    "repo_root": {"type": "string"},
                },
                "required": ["selector", "actual"],
            },
        ),
        T(
            name="perception_consistency_propose_fix",
            description=(
                "Consistency Intelligence (Phase 3): recommend fix for a deviation using graph standards. "
                "Composes fix.recommend query only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "standard_id": {"type": "string"},
                    "selector": {"type": "string"},
                    "actual": {"type": "object"},
                    "project_id": {"type": "string", "default": "default"},
                    "repo_root": {"type": "string"},
                },
                "required": ["standard_id"],
            },
        ),
        T(
            name="perception_coordinator_episode_start",
            description=(
                "Coordination Intelligence: start a coordinator episode and initialize PSM Runtime. "
                "Returns advisory briefing with next capability and compiled MCP tools. "
                "Host LLM remains the reasoner — coordinator is deterministic and advisory."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "default": "default"},
                    "cluster_id": {"type": "string", "description": "e.g. cluster.feature.form_pipeline"},
                    "playbook_id": {"type": "string", "description": "e.g. invalid_before_valid.form"},
                    "situation_class": {"type": "string"},
                    "lifecycle_stage": {"type": "string"},
                    "repo_root": {"type": "string"},
                    "website_url": {"type": "string"},
                    "session_id": {"type": "string"},
                    "intent": {"type": "string"},
                    "leaf_hint": {"type": "string", "description": "Telemetry only"},
                    "step_context": {"type": "object"},
                },
            },
        ),
        T(
            name="perception_coordinator_apply_envelope",
            description=(
                "Coordination Intelligence: normalize an MCP tool envelope into PSM Runtime and refresh briefing. "
                "Pass the envelope from any perception_* tool after invocation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "episode_id": {"type": "string"},
                    "envelope": {"type": "object", "description": "contract v1.0 envelope"},
                    "capability_id": {"type": "string", "description": "Optional T1 capability hint"},
                    "step_context": {"type": "object"},
                },
                "required": ["episode_id", "envelope"],
            },
        ),
        T(
            name="perception_coordinator_briefing",
            description=(
                "Coordination Intelligence: refresh advisory briefing from current PSM Runtime state."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "episode_id": {"type": "string"},
                    "step_context": {"type": "object"},
                },
                "required": ["episode_id"],
            },
        ),
    ]
