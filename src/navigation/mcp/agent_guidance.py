"""Actionable agent guidance for errors and degraded states (deterministic, no LLM)."""
from __future__ import annotations

import re
from typing import Any

# Exact degraded code -> recovery action
_DEGRADED_EXACT: dict[str, str] = {
    "integration_plan_only": "Dry-run only. Set execute_install:true to apply when user approves.",
    "installation_planner_partial": "Plan is partial. Pass repo_root (folder with package.json) and re-run.",
    "lighthouse_unavailable": "Install Node.js 18+ and run: npx playwright install chromium. Or set run_audits:false.",
    "lighthouse_no_evidence": "Lighthouse produced no scores. Retry with session on a loaded page URL.",
    "shadcn_ecosystem_unavailable": "Component catalog offline. Retry once; check network.",
    "registries_index_unavailable": "Registry index unavailable. Retry or use plan_only integrate.",
    "component_not_found": "No file match. Use perception_resolve_component or host IDE search.",
    "token_not_found": "Token not in project files. Check spelling or search CSS/Tailwind config.",
    "audit_no_snapshot": "Run perception_build_design_snapshot first (needs scan_id).",
    "graph_empty_run_refresh": "Run perception_design_graph_refresh with a recent scan_id.",
    "evaluation_without_repo_root": "Add repo_root pointing to your app root (package.json).",
    "deep_review_without_repo_root": "Add repo_root for codebase-aware review.",
    "figma_not_connected": "Run perception_figma_connect with PAT, or skip Figma tools.",
    "docs_provider_unavailable": "Framework docs provider offline. Use host IDE docs or retry.",
    "grounded_docs_cli_unavailable": "Install Node 18+ for grounded docs CLI.",
    "selection_empty_ranked_pool": "Broaden inspiration query or try perception_inspiration_discover.",
    "framework_context_unavailable": "Pass repo_root for framework-aware resource ranking.",
}

# Prefix patterns for dynamic degraded codes
_DEGRADED_PREFIX: list[tuple[str, str]] = [
    ("repo_root", "Set repo_root to your frontend app root (directory with package.json)."),
    ("scan_id", "Run perception_navigate_and_observe first; reuse scan_id from that response."),
    ("session_id", "Call perception_session_start; pass session_id to all browser tools."),
    ("lighthouse_", "Lighthouse audit issue. Ensure Node 18+ and page is fully loaded."),
    ("librecrawl_", "SEO crawl timeout. Use development SEO with scan_id reuse instead."),
    ("perception_scan_failed", "Browser observe failed. Check session_id and URL; re-observe."),
    ("discovery_missing_provider", "Inspiration provider unavailable. Try another query or provider."),
    ("inspiration_", "Inspiration rate limit or provider issue. Wait and retry."),
    ("gsc_discovery", "Google Search Console not linked. Use perception_seo_connect or skip GSC fields."),
    ("bing_discovery", "Bing Webmaster not configured. Optional — continue without Bing data."),
    ("ga4_discovery", "GA4 property match weak. Confirm website_url in seo_connect."),
]

_ERROR_EXACT: dict[str, str] = {
    "session_id required": "Call perception_session_start first; save session_id for browser tools.",
    "scan_id required": "Run perception_navigate_and_observe; save scan_id from the response.",
    "scan_not_found": "scan_id expired or wrong server. Re-run navigate_and_observe.",
    "snapshot_not_found": "Run perception_build_design_snapshot with a valid scan_id.",
    "session not found": "Session ended or invalid. Call perception_session_start again.",
    "claim object required": "Pass claim as JSON object. See perception://resolver-guide.",
    "path required": "Pass path (route) e.g. /forms/validation.",
    "name required": "Pass component name e.g. ValidationForm.",
    "url required": "Pass url (path or absolute URL).",
    "actions list required": "Pass actions array. Use perception_probe_form to discover fields first.",
}

_ERROR_CONTAINS: list[tuple[str, str]] = [
    ("Unknown session", "Call perception_session_start; use returned session_id."),
    ("unreachable", "Start dev server. Run perception_health again before session_start."),
    ("parallel", "Call MCP browser tools one at a time on the same session_id."),
]


def guidance_for_degraded(codes: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for code in codes:
        if not code or code in seen:
            continue
        seen.add(code)
        action = _DEGRADED_EXACT.get(code)
        if not action:
            for prefix, hint in _DEGRADED_PREFIX:
                if code.startswith(prefix) or prefix in code:
                    action = hint
                    break
        if not action:
            action = f"Review degraded code '{code}' in tool response data; adjust inputs and retry."
        out.append({"code": code, "agent_action": action})
    return out


def guidance_for_error(error: str | None) -> list[dict[str, str]]:
    if not error:
        return []
    text = error.strip()
    action = _ERROR_EXACT.get(text)
    if not action:
        lower = text.lower()
        for needle, hint in _ERROR_CONTAINS:
            if needle.lower() in lower:
                action = hint
                break
    if not action and "repo_root" in lower:
        action = "Set repo_root to your project root (absolute path to folder with package.json)."
    if not action and re.search(r"session", lower):
        action = "Start or restore browser session with perception_session_start."
    if not action:
        action = f"Fix input causing: {text[:120]}"
    return [{"code": "error", "message": text, "agent_action": action}]


def attach_guidance(envelope: dict[str, Any]) -> dict[str, Any]:
    """Add agent_guidance list to envelope from error + degraded (non-mutating copy)."""
    degraded = list(envelope.get("degraded") or [])
    error = envelope.get("error")
    guidance: list[dict[str, str]] = []
    guidance.extend(guidance_for_error(error if not envelope.get("ok") else None))
    guidance.extend(guidance_for_degraded(degraded))
    if not guidance:
        return envelope
    out = dict(envelope)
    out["agent_guidance"] = guidance
    return out
