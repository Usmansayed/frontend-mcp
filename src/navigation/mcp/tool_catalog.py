"""Tool grouping, ordering, description/schema enrichment for MCP discoverability."""
from __future__ import annotations

import copy
import re
from typing import Any

# Display order for tools/list (lower = earlier)
GROUP_ORDER: dict[str, int] = {
    "Session": 10,
    "Browser": 20,
    "Quality": 30,
    "Resolver": 40,
    "Component": 50,
    "Design": 60,
    "SEO": 70,
    "Resources": 80,
    "Inspiration": 85,
    "Figma": 90,
    "Diagnostics": 100,
    "Coordinator": 110,
}

# Explicit overrides (others inferred by rules below)
_TOOL_GROUP: dict[str, str] = {
    "perception_health": "Session",
    "perception_session_start": "Session",
    "perception_session_end": "Session",
    "perception_state_save": "Session",
    "perception_state_restore": "Session",
    "perception_state_list": "Session",
    "perception_flow_describe": "Browser",
    "perception_code_context": "Resolver",
    "perception_coordinator_episode_start": "Coordinator",
    "perception_coordinator_apply_envelope": "Coordinator",
    "perception_coordinator_briefing": "Coordinator",
}

# Per-tool workflow lines (what / when / before / next) — concise MCP best practice
_WORKFLOW: dict[str, dict[str, str]] = {
    "perception_health": {
        "what": "Ping dev server; confirm MCP envelope.",
        "when": "First call every task.",
        "before": "—",
        "next": "perception_session_start",
    },
    "perception_session_start": {
        "what": "Launch browser session.",
        "when": "After health OK.",
        "before": "perception_health",
        "next": "perception_navigate_and_observe",
    },
    "perception_session_end": {
        "what": "Close browser; release resources.",
        "when": "Task complete.",
        "before": "final perception_verify",
        "next": "—",
    },
    "perception_navigate_and_observe": {
        "what": "Navigate + snapshot DOM, a11y, dev insights, screenshots.",
        "when": "Inspect or baseline a page.",
        "before": "perception_session_start",
        "next": "perception_verify or code edits",
    },
    "perception_observe": {
        "what": "Snapshot current page without navigate.",
        "when": "After in-page actions.",
        "before": "execute_script / execute_actions",
        "next": "perception_verify",
    },
    "perception_verify": {
        "what": "Assert UI criteria (url, text, elements).",
        "when": "After every code change or browser act.",
        "before": "observe or act",
        "next": "STOP if pass; else diff + fix",
    },
    "perception_diff": {
        "what": "Compare two scan screenshots/DOM.",
        "when": "Verify failed or regression check.",
        "before": "two observe scans",
        "next": "fix code + verify",
    },
    "perception_resolve_route": {
        "what": "Map route path → source file.",
        "when": "Before editing page code.",
        "before": "navigate_and_observe (optional)",
        "next": "edit file + verify",
    },
    "perception_validate_route_claim": {
        "what": "Validate your route→file guess.",
        "when": "resolve_route status ambiguous.",
        "before": "perception_resolve_route",
        "next": "edit matched file",
    },
    "perception_correlate_live": {
        "what": "Cross-check live DOM vs resolution.",
        "when": "After resolve + observe.",
        "before": "scan_id + resolution",
        "next": "verify",
    },
    "perception_search_components": {
        "what": "Rank shadcn/Radix component candidates.",
        "when": "User wants a UI widget.",
        "before": "—",
        "next": "integrate_component plan_only",
    },
    "perception_integrate_component": {
        "what": "Plan or apply component integration.",
        "when": "After search; use plan_only first.",
        "before": "search_components",
        "next": "verify UI",
    },
    "perception_seo_audit_start": {
        "what": "Start SEO audit (dev=inline, pro=async).",
        "when": "After observe; pass scan_id.",
        "before": "navigate_and_observe",
        "next": "seo_audit_poll (pro only)",
    },
    "perception_seo_audit_poll": {
        "what": "Poll professional SEO job.",
        "when": "After seo_audit_start returns job_id.",
        "before": "seo_audit_start",
        "next": "seo_verify",
    },
    "perception_probe_form": {
        "what": "Discover form fields and selectors.",
        "when": "Before filling unknown forms.",
        "before": "navigate to form page",
        "next": "invalid submit verify, then valid fill",
    },
    "perception_console_get": {
        "what": "Filter console log entries.",
        "when": "Debugging; need detail:full or console_get.",
        "before": "observe with detail:full",
        "next": "fix + verify",
    },
    "perception_network_get": {
        "what": "Filter network log entries.",
        "when": "Debugging API calls.",
        "before": "observe with detail:full",
        "next": "fix + verify",
    },
}

_COMMON_SCHEMA_EXAMPLES: dict[str, Any] = {
    "session_id": {"type": "string", "description": "From perception_session_start", "examples": ["sess_a1b2c3"]},
    "scan_id": {"type": "string", "description": "From navigate_and_observe or observe", "examples": ["scan_x9y8z7"]},
    "repo_root": {
        "type": "string",
        "description": "Absolute path to app root (package.json). Env: FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT",
        "examples": ["/path/to/my-app"],
    },
    "url": {"type": "string", "description": "Path or absolute URL", "examples": ["/forms/validation", "http://localhost:5173/"]},
    "base_url": {"type": "string", "examples": ["http://localhost:5173"]},
}

_DETAIL_ENUM_DOC = (
    "summary_only (default): agent_summary + images, no observation blob. "
    "Use full when debugging console/network (entries in observation). "
    "metadata_only: agent_summary only, no images."
)


def infer_group(name: str) -> str:
    if name in _TOOL_GROUP:
        return _TOOL_GROUP[name]
    if name in ("perception_health", "perception_session_start", "perception_session_end") or "state_" in name:
        return "Session"
    if any(
        name.endswith(s)
        for s in (
            "_navigate",
            "_observe",
            "_verify",
            "_diff",
            "_execute_script",
            "_execute_actions",
            "_auth_gate",
            "_probe_form",
            "_probe_guards",
            "_flow_describe",
        )
    ) or name in ("perception_navigate", "perception_observe", "perception_navigate_and_observe"):
        return "Browser"
    if "console_" in name or "network_" in name:
        return "Quality"
    if "resolve_" in name or "validate_" in name or "correlate_live" in name or name == "perception_code_context":
        return "Resolver"
    if "component" in name or "integrate_component" in name or "search_components" in name:
        return "Component"
    if name.startswith("perception_design_") or name.startswith("perception_consistency_") or name == "perception_build_design_snapshot":
        return "Design"
    if name.startswith("perception_seo_"):
        return "SEO"
    if name.startswith("perception_resource_"):
        return "Resources"
    if name.startswith("perception_inspiration_"):
        return "Inspiration"
    if name.startswith("perception_figma_"):
        return "Figma"
    if any(x in name for x in ("audit_", "diagnosis", "debug_mode", "detect_framework", "framework_docs", "full_diagnosis")):
        return "Diagnostics"
    if name.startswith("perception_coordinator_"):
        return "Coordinator"
    return "Browser"


def _infer_workflow(name: str) -> dict[str, str]:
    if name in _WORKFLOW:
        return _WORKFLOW[name]
    group = infer_group(name)
    if group == "Resolver":
        return {
            "what": "Code↔UI resolver lookup.",
            "when": "Before file edits.",
            "before": "read perception://resolver-guide",
            "next": "edit + verify",
        }
    if group == "SEO":
        return {"what": "SEO intelligence.", "when": "SEO tasks.", "before": "seo_status", "next": "verify or report"}
    if group == "Diagnostics":
        return {"what": "Lighthouse/diagnosis.", "when": "Quality audit.", "before": "loaded page", "next": "review scores"}
    return {"what": "See description.", "when": "As needed.", "before": "AGENT_GUIDE", "next": "verify"}


def format_description(name: str, original: str) -> str:
    group = infer_group(name)
    wf = _infer_workflow(name)
    dep = " [DEPRECATED]" if name == "perception_code_context" else ""
    body = original.strip()
    labels = ("Does:", "Use when:", "Returns:", "Next:")
    if all(label in body for label in labels):
        return f"[{group}]{dep} {body}"
    if len(body) > 180:
        body = body[:177] + "..."
    return (
        f"[{group}]{dep} Does: {wf['what']} "
        f"Use when: {wf['when']} "
        "Returns: a structured MCP envelope with evidence quality and artifacts when available. "
        f"Next: {wf['next']}. Details: {body}"
    )


def _enhance_schema(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(schema)
    props = out.setdefault("properties", {})
    for key, spec in _COMMON_SCHEMA_EXAMPLES.items():
        if key in props and isinstance(props[key], dict):
            props[key] = {**props[key], **{k: v for k, v in spec.items() if k not in props[key] or k == "examples"}}
    if "detail" in props and isinstance(props["detail"], dict):
        props["detail"]["description"] = _DETAIL_ENUM_DOC
    if "criteria" in props:
        props["criteria"].setdefault(
            "examples",
            [{"url_contains": ["/forms/validation"], "text_contains": ["Submit"]}],
        )
    if name == "perception_validate_route_claim" and "claim" in props:
        props["claim"].setdefault(
            "examples",
            [{"route": "/forms/validation", "file": "src/pages/forms/ValidationForm.jsx", "component": {"name": "ValidationForm"}}],
        )
    if name == "perception_seo_audit_start":
        props.setdefault("scan_id", _COMMON_SCHEMA_EXAMPLES["scan_id"])
        out.setdefault("examples", [{"website_url": "http://localhost:5173", "scan_id": "scan_abc", "repo_root": "/path/to/app"}])
    return out


def _tool_sort_key(tool: Any) -> tuple[int, str]:
    name = tool.name
    group = infer_group(name)
    return (GROUP_ORDER.get(group, 999), name)


def apply_tool_catalog(tools: list[Any], tool_type: Any) -> list[Any]:
    """Sort tools by group and enrich description, schema, _meta."""
    enriched: list[Any] = []
    for tool in tools:
        name = tool.name
        group = infer_group(name)
        order = GROUP_ORDER.get(group, 999)
        desc = format_description(name, tool.description or "")
        schema = _enhance_schema(name, tool.inputSchema or {"type": "object", "properties": {}})
        meta = {"group": group, "group_order": order, "tool_order": _tool_sort_key(tool)}
        kwargs: dict[str, Any] = {
            "name": name,
            "description": desc,
            "inputSchema": schema,
            "_meta": {"perception": meta},
        }
        if hasattr(tool, "title") and tool.title:
            kwargs["title"] = f"{group}: {name.replace('perception_', '')}"
        if hasattr(tool, "annotations") and tool.annotations:
            kwargs["annotations"] = tool.annotations
        try:
            enriched.append(tool_type(**kwargs))
        except TypeError:
            meta_val = kwargs.pop("_meta", None)
            kwargs.pop("title", None)
            t = tool_type(
                name=kwargs["name"],
                description=kwargs["description"],
                inputSchema=kwargs["inputSchema"],
            )
            if meta_val is not None:
                setattr(t, "_meta", meta_val)
            enriched.append(t)
    enriched.sort(key=_tool_sort_key)
    return enriched


def group_summary(tools: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in tools:
        g = infer_group(t.name)
        counts[g] = counts.get(g, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: GROUP_ORDER.get(kv[0], 999)))
