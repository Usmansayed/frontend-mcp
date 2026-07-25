"""MCP tool definitions (schemas + playbook descriptions)."""
from __future__ import annotations

from typing import Any


def perception_tools(mcp_types: Any) -> list[Any]:
    """Return Tool list; mcp_types is mcp.types when MCP is installed."""
    from navigation.mcp.tool_catalog import apply_tool_catalog

    T = mcp_types.Tool
    return apply_tool_catalog(
        [
        T(
            name="perception_health",
            description=(
                "Does: checks runtime reachability and bootstraps Engineering Strategy from intent. "
                "Use when: FIRST call of any UI/frontend/visual task — before planning or coding a full viewport. "
                "Returns: reachability plus recommended_resource and implementation_gate. "
                "Next: read recommended_resource; session_start if reachable; never skip to end-of-task verify."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Base URL, e.g. http://127.0.0.1:18765"},
                    "intent": {
                        "type": "string",
                        "description": (
                            "Real user task (e.g. 'Build a SaaS dashboard'). Required for "
                            "useful coordinator bootstrap — without intent, greenfield vs "
                            "hotfix routing is weak."
                        ),
                    },
                },
            },
        ),
        T(
            name="perception_session_start",
            description=(
                "Does: starts the owned browser session and creates the task's coordinator episode. "
                "Use when: immediately after health when reachable — required before observe/verify evidence. "
                "Returns: reusable session_id, Engineering Strategy, required resource, and readiness gate. "
                "Next: obey implementation_gate; gather minimum evidence; do not draft full UI while blocked."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "base_url": {"type": "string", "description": "App base URL"},
                    "intent": {
                        "type": "string",
                        "description": (
                            "Required for structural UI: natural-language task intent "
                            "(e.g. 'Build a SaaS dashboard', 'Production hotfix for login'). "
                            "Drives coordinator phase + agent_summary.engineering_strategy. "
                            "Omit only for pure connectivity smoke."
                        ),
                    },
                    "repo_root": {
                        "type": "string",
                        "description": "Optional absolute repo root for codebase evidence routing",
                    },
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
                        "enum": ["full", "summary_only", "metadata_only"],
                        "default": "summary_only",
                        "description": (
                            "summary_only (default): agent_summary + visual_insights, no DOM. "
                            "metadata_only: agent_summary only, no images. "
                            "full: includes observation DOM payload."
                        ),
                    },
                    "no_images": {
                        "type": "boolean",
                        "default": False,
                        "description": "Skip screenshot capture and inline images (lighter than summary_only when visual_insights not needed).",
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
                        "enum": ["full", "summary_only", "metadata_only"],
                        "default": "summary_only",
                        "description": (
                            "summary_only (default): agent_summary + visual_insights, no DOM. "
                            "metadata_only: agent_summary only, no images. "
                            "full: includes observation DOM payload."
                        ),
                    },
                    "no_images": {
                        "type": "boolean",
                        "default": False,
                        "description": "Skip screenshot capture and inline images.",
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
                "Does: asserts URL, text, and JavaScript success criteria and captures failure evidence. "
                "Use when: after every UI action; never as a substitute for skipped bootstrap. "
                "Returns: data.verified (transport ok is not a pass), checklist, blocking findings. "
                "Next: fix on fail; claim-done only after Done ladder (verify + sections + ship when required)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "section_id": {
                        "type": "string",
                        "description": (
                            "Optional layout section id from section_checklist "
                            "(e.g. main:0). Injects scoped JS assertions and marks that section verified."
                        ),
                    },
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
                            "section_id": {"type": "string"},
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
                "DEPRECATED for agent hot paths — heavy Grounded Docs fetch. "
                "Prefer host Context7 / IDE docs. Detect + fetch version-aware framework "
                "documentation on demand via Grounded Docs. Requires Node.js 22+ (npx). "
                "Override with GROUNDED_DOCS_CLI / GROUNDED_DOCS_STORE_PATH."
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
                "Does: builds a deterministic Component Intelligence search plan without provider calls. "
                "Use when: the component or foundation request is broad or ambiguous. "
                "Returns: intent, expanded terms, style hints, registries, and multi-pass queries. "
                "Next: refine if needed, then search/select; planning alone does not resolve foundation."
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
                "Does: searches and selects a foundation using framework, codebase, design, and consistency evidence. "
                "Use when: component foundation is an unresolved structural decision. "
                "Returns: chosen candidate, runners-up, compatibility findings, and rationale. "
                "Next: resolve blockers, then adapt/integrate the selected foundation."
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
                "Component Intelligence. Fast integration plan by default (<5s): search (or candidate_id) → "
                "select foundation → dependencies + install steps + next actions. Set execute_install=true "
                "only when the user explicitly wants mutating install/repair."
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
                    "plan_only": {
                        "type": "boolean",
                        "default": True,
                        "description": "Return partial plan quickly without mutating the repo (default).",
                    },
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
                    "repo_root": {
                        "type": "string",
                        "description": "Project root for stack/hints scoring (avoids hints_without_repo_root)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional browser session — inherits repo_root from episode when omitted",
                    },
                },
                "required": ["query"],
            },
        ),
        T(
            name="perception_inspiration_collect",
            description=(
                "Does: collects 3–5 deduplicated image-first references as ephemeral host-viewable blobs. "
                "Use when: design direction is unresolved and strategy assigns inspiration high ROI. "
                "Returns: references, blob quality, provisional Engineering Spec priors, and evidence outcome. "
                "Next: inspect images and harden priors with measured design evidence; use browser fallback only when directed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Inspiration search query"},
                    "session_id": {
                        "type": "string",
                        "description": "Browser session — binds seed Spec to episode when present",
                    },
                    "bind_as_reference": {
                        "type": "boolean",
                        "default": True,
                        "description": "Bind inspiration seed Spec as reference for SpecDiff gate",
                    },
                    "per_provider": {"type": "integer", "default": 4},
                    "target_refs": {
                        "type": "integer",
                        "default": 5,
                        "description": "Stop after this many high-quality image refs (default 5)",
                    },
                    "min_refs": {
                        "type": "integer",
                        "default": 3,
                        "description": "Minimum image refs before early-stop is allowed",
                    },
                    "allow_browser_screenshot": {
                        "type": "boolean",
                        "default": False,
                        "description": "Last-resort browser screenshot when no CDN/og:image exists",
                    },
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
            description=(
                "Resource Intelligence. Structured license check for a resource asset. "
                "asset.license may be a LicenseProfile object "
                "({spdx_id|name, commercial_use, ...}) or a flat SPDX/name string (e.g. \"ISC\")."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "asset": {
                        "type": "object",
                        "description": (
                            "Asset dict. license may be string (\"MIT\") or object "
                            "({spdx_id|name, commercial_use, attribution_required, ...})."
                        ),
                        "properties": {
                            "provider_id": {"type": "string"},
                            "license": {
                                "oneOf": [
                                    {"type": "string", "description": "SPDX or common name, e.g. ISC"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "spdx_id": {"type": "string"},
                                            "name": {"type": "string"},
                                            "commercial_use": {"type": "boolean"},
                                            "attribution_required": {"type": "boolean"},
                                        },
                                    },
                                ]
                            },
                        },
                    },
                    "commercial_required": {"type": "boolean", "default": True},
                    "attribution_ok": {"type": "boolean", "default": True},
                    "query": {"type": "string"},
                },
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
        # SEO Intelligence tools excluded from MVP — see parked/MVP_EXCLUDE_SEO.md
        # Figma Intelligence tools excluded from MVP — see parked/MVP_EXCLUDE_FIGMA.md
        T(
            name="perception_visual_feedback",
            description=(
                "Does: the common LOOK → judge → act loop for ANY UI work. Captures a purpose-shaped "
                "screenshot pack (viewport/full/section/element) with inline images, returns the exact "
                "feedback JSON schema to fill for that purpose, and — when you pass visual_feedback back — "
                "advisory next_actions. "
                "Use when: before/after design, consistency, component, inspiration, hotfix, or forms changes; "
                "whenever you must know how the page LOOKS before locking a decision. "
                "Returns: inline screenshots, purpose, recommended_resource guide, feedback_schema/feedback_prompt "
                "(LOOK phase) or normalized visual_feedback + next_actions (judgment phase). "
                "Next: LOOK at the images, fill visual_feedback per feedback_schema, call again, then act on next_actions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Live capture (preferred)"},
                    "scan_id": {"type": "string", "description": "Reuse stored screenshot when live capture unavailable"},
                    "purpose": {
                        "type": "string",
                        "enum": ["design", "consistency", "component", "inspiration", "hotfix", "forms", "general"],
                        "default": "general",
                        "description": "Why you are looking — picks pack default, guide, and feedback schema",
                    },
                    "screenshot_pack": {
                        "type": "string",
                        "enum": ["auto", "design", "viewport", "full", "section", "element", "none"],
                        "default": "auto",
                        "description": "auto = purpose default. design=viewport+full+sections.",
                    },
                    "screenshot_selector": {
                        "type": "string",
                        "description": "CSS selector for element crop (forces pack=element when set)",
                    },
                    "focus_sections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Semantic blocks to prioritize for section crops, e.g. ['header','hero']",
                    },
                    "max_sections": {"type": "integer", "default": 3},
                    "include_screenshots": {
                        "type": "boolean",
                        "default": True,
                        "description": "false = process visual_feedback only, no new captures",
                    },
                    "visual_feedback": {
                        "type": "object",
                        "description": (
                            "Your judgment AFTER looking at the images. Shape follows feedback_schema for the purpose: "
                            "{judgment: ok|needs_work|unclear, notes, focus_sections[], focus_selector, issues[], "
                            "+ purpose extras (borrow/ignore, standard_hints, field_issues, ...)}. Drives next_actions."
                        ),
                    },
                    "visual_notes": {"type": "string", "description": "Flat alias for visual_feedback.notes"},
                    "visual_judgment": {
                        "type": "string",
                        "enum": ["ok", "needs_work", "unclear"],
                        "description": "Flat alias for visual_feedback.judgment",
                    },
                },
            },
        ),
        T(
            name="perception_build_design_snapshot",
            description=(
                "Does: measures a Design Snapshot and Frontend Engineering Spec from live scan evidence. "
                "Use when: before structural redesign decisions, when binding a measured reference, and after a draft. "
                "Returns: geometry/tokens/components, Spec coverage, reference binding quality, SpecDiff gate, and "
                "inline rendered screenshots (annotated viewport + full page + section crops) — LOOK at them, "
                "then pass visual_feedback so next_actions guide the next edit. "
                "Next: resolve low coverage or revise required drifts before verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "scan_id": {"type": "string", "description": "Preferred — from perception_observe"},
                    "snapshot_id": {"type": "string", "description": "Return existing snapshot"},
                    "bind_as_reference": {
                        "type": "boolean",
                        "default": False,
                        "description": "Bind compiled Spec as reference for later SpecDiff revision gate",
                    },
                    "role": {
                        "type": "string",
                        "enum": ["current", "reference"],
                        "description": "Alias for bind: role=reference binds Spec as reference",
                    },
                    "reference_engineering_spec": {
                        "type": "object",
                        "description": "Optional explicit reference Spec (overrides episode bind)",
                    },
                    "use_designlang": {
                        "type": "boolean",
                        "default": False,
                        "description": "Augment with designlang CLI when DESIGNLANG_ENABLED=1",
                    },
                    "include_screenshots": {
                        "type": "boolean",
                        "default": True,
                        "description": "Attach rendered screenshots (default on for design/consistency)",
                    },
                    "screenshot_pack": {
                        "type": "string",
                        "enum": ["auto", "design", "viewport", "full", "section", "element", "none"],
                        "default": "auto",
                        "description": (
                            "auto→design pack for these tools (viewport+full+sections). "
                            "Narrow with section/element when visual_feedback focuses a block."
                        ),
                    },
                    "screenshot_selector": {
                        "type": "string",
                        "description": "CSS selector — also attach a cropped screenshot of this element",
                    },
                    "max_sections": {
                        "type": "number",
                        "default": 3,
                        "description": "Max number of section crops (header/nav/main/footer/...) to attach",
                    },
                    "focus_sections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Prefer these section roles/labels in crops (e.g. header, footer, hero)",
                    },
                    "visual_feedback": {
                        "type": "object",
                        "description": (
                            "Agent judgment after LOOKING at screenshots. Drives next_actions "
                            "(remeasure, verify section, propose_fix, edit_then_remeasure)."
                        ),
                        "properties": {
                            "judgment": {
                                "type": "string",
                                "enum": ["ok", "needs_work", "unclear"],
                            },
                            "notes": {"type": "string"},
                            "focus_sections": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "focus_selector": {"type": "string"},
                            "issues": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "section": {"type": "string"},
                                        "selector": {"type": "string"},
                                        "problem": {"type": "string"},
                                        "wanted": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "visual_notes": {
                        "type": "string",
                        "description": "Flat alias for visual_feedback.notes",
                    },
                    "visual_judgment": {
                        "type": "string",
                        "enum": ["ok", "needs_work", "unclear"],
                        "description": "Flat alias for visual_feedback.judgment",
                    },
                },
            },
        ),
        T(
            name="perception_design_review",
            description=(
                "Does: reviews a measured snapshot (review mode) or runs Ship Council challenges (mode=ship). "
                "Use when: a draft exists; use ship after verify on structural/balanced work before claim-done. "
                "Returns: review findings and SpecDiff (or ROI-ranked ship challenges, ship_gate, ship_summary) plus "
                "inline rendered screenshots (annotated viewport + full page + section crops) — LOOK at them and "
                "pass visual_feedback so next_actions guide the next edit. "
                "Next: revise challenges, accept with engineering rationale, or remeasure after revisions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "scan_id": {"type": "string"},
                    "snapshot_id": {"type": "string"},
                    "user_task": {"type": "string", "description": "What the user is trying to accomplish"},
                    "repo_root": {
                        "type": "string",
                        "description": (
                            "Repo root containing ForOpenCode/ (UX Knowledge Brain) for "
                            "design_review ux_knowledge provider; also used for PDG enrichment"
                        ),
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["review", "ship"],
                        "default": "review",
                        "description": "review=Design Review; ship=Ship Council post-draft gate",
                    },
                    "dispositions": {
                        "type": "array",
                        "description": "Ship mode only: challenge dispositions (revised, accepted, ask_user)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "signal": {"type": "string"},
                                "decision_id": {"type": "string"},
                                "disposition": {
                                    "type": "string",
                                    "enum": ["revised", "accepted", "ask_user"],
                                },
                                "reason": {"type": "string"},
                                "accept_reason": {"type": "string"},
                            },
                        },
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["page", "flow", "feature", "component", "region"],
                        "default": "page",
                    },
                    "compare_references": {
                        "type": "boolean",
                        "default": True,
                        "description": "Fallback to design-reference-registry when no Spec bound",
                    },
                    "reference_engineering_spec": {
                        "type": "object",
                        "description": "Optional explicit reference Spec",
                    },
                    "use_designlang": {"type": "boolean", "default": False},
                    "include_screenshots": {
                        "type": "boolean",
                        "default": True,
                        "description": "Attach rendered screenshots (default on for design/consistency)",
                    },
                    "screenshot_pack": {
                        "type": "string",
                        "enum": ["auto", "design", "viewport", "full", "section", "element", "none"],
                        "default": "auto",
                        "description": (
                            "auto→design pack (viewport+full+sections). "
                            "Narrow with section/element when visual_feedback focuses a block."
                        ),
                    },
                    "screenshot_selector": {
                        "type": "string",
                        "description": "CSS selector — also attach a cropped screenshot of this element",
                    },
                    "max_sections": {
                        "type": "number",
                        "default": 3,
                        "description": "Max number of section crops to attach",
                    },
                    "focus_sections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Prefer these section roles/labels in crops",
                    },
                    "visual_feedback": {
                        "type": "object",
                        "description": (
                            "Agent judgment after LOOKING at screenshots. Returns next_actions "
                            "to remeasure, verify section, propose_fix, or edit_then_remeasure."
                        ),
                        "properties": {
                            "judgment": {
                                "type": "string",
                                "enum": ["ok", "needs_work", "unclear"],
                            },
                            "notes": {"type": "string"},
                            "focus_sections": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "focus_selector": {"type": "string"},
                            "issues": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "section": {"type": "string"},
                                        "selector": {"type": "string"},
                                        "problem": {"type": "string"},
                                        "wanted": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "visual_notes": {
                        "type": "string",
                        "description": "Flat alias for visual_feedback.notes",
                    },
                    "visual_judgment": {
                        "type": "string",
                        "enum": ["ok", "needs_work", "unclear"],
                        "description": "Flat alias for visual_feedback.judgment",
                    },
                },
            },
        ),
        T(
            name="perception_consistency_review",
            description=(
                "Consistency Intelligence: refresh Project Design Graph from snapshot + codebase/tokens, "
                "then batch-audit interactive elements against learned standards. "
                "Attaches viewport + full page + section screenshots — LOOK at them, then pass "
                "visual_feedback so next_actions guide propose_fix / section edits."
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
                    "include_screenshots": {
                        "type": "boolean",
                        "default": True,
                        "description": "Attach rendered screenshots (default on)",
                    },
                    "screenshot_pack": {
                        "type": "string",
                        "enum": ["auto", "design", "viewport", "full", "section", "element", "none"],
                        "default": "auto",
                    },
                    "screenshot_selector": {"type": "string"},
                    "max_sections": {"type": "number", "default": 3},
                    "focus_sections": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "visual_feedback": {
                        "type": "object",
                        "description": "Agent visual judgment → next_actions",
                        "properties": {
                            "judgment": {
                                "type": "string",
                                "enum": ["ok", "needs_work", "unclear"],
                            },
                            "notes": {"type": "string"},
                            "focus_sections": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "focus_selector": {"type": "string"},
                            "issues": {"type": "array", "items": {"type": "object"}},
                        },
                    },
                    "visual_notes": {"type": "string"},
                    "visual_judgment": {
                        "type": "string",
                        "enum": ["ok", "needs_work", "unclear"],
                    },
                },
            },
        ),
        T(
            name="perception_consistency_audit",
            description=(
                "Consistency Intelligence: batch audit snapshot elements against populated Project Design Graph. "
                "Run perception_design_graph_refresh first if graph is empty. "
                "Attaches viewport + full page + section screenshots — LOOK at them, then pass "
                "visual_feedback so next_actions guide propose_fix / section edits."
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
                    "include_screenshots": {
                        "type": "boolean",
                        "default": True,
                        "description": "Attach rendered screenshots (default on)",
                    },
                    "screenshot_pack": {
                        "type": "string",
                        "enum": ["auto", "design", "viewport", "full", "section", "element", "none"],
                        "default": "auto",
                    },
                    "screenshot_selector": {"type": "string"},
                    "max_sections": {"type": "number", "default": 3},
                    "focus_sections": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "visual_feedback": {
                        "type": "object",
                        "description": "Agent visual judgment → next_actions",
                        "properties": {
                            "judgment": {
                                "type": "string",
                                "enum": ["ok", "needs_work", "unclear"],
                            },
                            "notes": {"type": "string"},
                            "focus_sections": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "focus_selector": {"type": "string"},
                            "issues": {"type": "array", "items": {"type": "object"}},
                        },
                    },
                    "visual_notes": {"type": "string"},
                    "visual_judgment": {
                        "type": "string",
                        "enum": ["ok", "needs_work", "unclear"],
                    },
                },
            },
        ),
        T(
            name="perception_design_knowledge_query",
            description=(
                "Knowledge API: query Project Design Graph OR ForOpenCode UX Knowledge Brain. "
                "For UX engineering guidance use query_id `ux.retrieve` with params: "
                "intent, surface_type (landing|dashboard|forms|...), phase, task, ui_component, problem. "
                "Returns playbook, decisions, patterns, principles, conflicts, evidence. "
                "Legacy PDG queries: graph.summary, standard.for_context, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query_id": {
                        "type": "string",
                        "description": "ux.retrieve | graph.summary | ...",
                    },
                    "params": {
                        "type": "object",
                        "description": "For ux.retrieve: intent, surface_type, phase, task, ui_component, user_flow, problem",
                    },
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
                "Coordination Intelligence: start or reuse a coordinator episode and initialize PSM Runtime. "
                "DEFAULT: if session_id is already bound to a live episode, REUSE it (preserves budget, "
                "evidence, and implementation gate). Pass force_new=true for an explicit hard reset that "
                "does NOT merge prior episode state. Returns advisory briefing with next capability."
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
                    "force_new": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "If true, always mint a fresh episode (hard reset). "
                            "Default false reuses the session's existing episode."
                        ),
                    },
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
    ],
        T,
    )
