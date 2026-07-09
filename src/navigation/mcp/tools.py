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
                "Playbook: code ↔ UI correlation (AGENT_GUIDE §10). query_type: stats, search, get_route. "
                "Supplements observe — does not replace it."
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
    ]
