"""Execution tier classification — SYNC_FAST vs SYNC_OFFLOAD vs BACKGROUND."""

from __future__ import annotations

from enum import Enum


class ExecutionTier(str, Enum):
    SYNC_FAST = "sync_fast"
    SYNC_OFFLOAD = "sync_offload"
    BACKGROUND = "background"


# Tools that run blocking sync work without browser/session — safe to isolate in thread pool.
_SYNC_OFFLOAD_TOOLS: frozenset[str] = frozenset(
    {
        "perception_code_context",
        "perception_framework_docs",
        "perception_detect_framework",
        "perception_resolve_route",
        "perception_validate_route_claim",
        "perception_resolve_component",
        "perception_validate_component_claim",
        "perception_resolve_design_token",
        "perception_resolve_state_owner",
        "perception_resolve_api_endpoint",
        "perception_resolve_layout",
        "perception_correlate_live",
    }
)

# Start returns immediately; development runs inline, professional enqueues background work.
_SYNC_FAST_SEO_TOOLS: frozenset[str] = frozenset(
    {
        "perception_seo_audit_start",
    }
)


def tier_for_tool(tool: str) -> ExecutionTier:
    if tool in _SYNC_FAST_SEO_TOOLS:
        return ExecutionTier.SYNC_FAST
    if tool in _SYNC_OFFLOAD_TOOLS:
        return ExecutionTier.SYNC_OFFLOAD
    if tool.startswith("perception_audit_") or tool == "perception_audit_mode":
        # Lighthouse subprocess is offloaded inside run_audit; keep on main loop for session URL.
        return ExecutionTier.SYNC_FAST
    return ExecutionTier.SYNC_FAST
