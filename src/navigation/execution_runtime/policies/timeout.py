"""Timeout policies — per-tool deterministic limits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Lighthouse category subprocess default (also schema default).
DEFAULT_AUDIT_TIMEOUT_S = 120.0
# Hard ceiling so a huge timeout_s cannot pin the MCP process forever.
MAX_AUDIT_TIMEOUT_S = 600.0
# audit_mode / full_diagnosis run multiple Lighthouse categories sequentially.
_MULTI_AUDIT_CATEGORY_COUNT = {
    "perception_audit_mode": 4,
    "perception_full_diagnosis": 4,
}


@dataclass(frozen=True)
class TimeoutPolicy:
    default_seconds: float = 60.0
    per_tool_seconds: dict[str, float] = field(default_factory=dict)

    def timeout_for(self, tool: str, args: dict[str, Any] | None = None) -> float:
        args = args or {}
        if tool in self.per_tool_seconds:
            return self.per_tool_seconds[tool]

        # Lighthouse-backed tools: honor caller timeout_s (was ignored by fixed 120s wall).
        if tool.startswith("perception_audit_") or tool == "perception_full_diagnosis":
            return self._audit_wall_timeout(tool, args)

        if tool == "perception_health":
            return 10.0
        if tool.startswith("perception_resolve_") or tool.startswith("perception_validate_"):
            return 2.0
        if tool == "perception_correlate_live":
            return 5.0
        return self.default_seconds

    def _audit_wall_timeout(self, tool: str, args: dict[str, Any]) -> float:
        explicit = args.get("timeout_s") is not None
        try:
            requested = float(args.get("timeout_s") if explicit else DEFAULT_AUDIT_TIMEOUT_S)
        except (TypeError, ValueError):
            requested = DEFAULT_AUDIT_TIMEOUT_S
            explicit = False
        per_category = max(30.0, min(requested, MAX_AUDIT_TIMEOUT_S))
        categories = _MULTI_AUDIT_CATEGORY_COUNT.get(tool, 1)
        # Wall must cover sequential categories + small overhead.
        wall = per_category * categories + (15.0 if categories > 1 else 5.0)
        capped = min(wall, MAX_AUDIT_TIMEOUT_S * categories)
        # Honor explicit short timeout_s (previously floored to 120s → looked ignored).
        if explicit:
            return capped
        return max(DEFAULT_AUDIT_TIMEOUT_S, capped)


DEFAULT_TIMEOUT_POLICY = TimeoutPolicy(
    per_tool_seconds={
        "perception_health": 10.0,
        "perception_flow_describe": 15.0,
        "perception_code_context": 30.0,
        # Component search/select can hit many registries — keep generous.
        "perception_select_component_foundation": 35.0,
        "perception_search_components": 35.0,
        "perception_plan_component_search": 20.0,
        "perception_integrate_component": 30.0,
        "perception_observe": 45.0,
        "perception_navigate_and_observe": 45.0,
        "perception_visual_feedback": 45.0,
    },
)
