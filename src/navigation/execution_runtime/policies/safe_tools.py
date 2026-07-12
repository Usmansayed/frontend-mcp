"""Safe-tool registry — idempotency and retry eligibility."""

from __future__ import annotations

from dataclasses import dataclass, field


# Read-only / observe / query tools — safe to retry and deduplicate by default.
_SAFE_TOOLS = frozenset({
    "perception_health",
    "perception_observe",
    "perception_navigate_and_observe",
    "perception_navigate",
    "perception_flow_describe",
    "perception_code_context",
    "perception_detect_framework",
    "perception_framework_docs",
    "perception_console_get",
    "perception_network_get",
    "perception_seo_query",
    "perception_seo_status",
    "perception_figma_status",
    "perception_design_knowledge_query",
    "perception_design_graph_summary",
    "perception_diff",
    "perception_state_list",
    "perception_coordinator_briefing",
    "perception_probe_form",
    "perception_probe_guards",
    "perception_plan_component_search",
    "perception_search_components",
})

# Mutating tools — never auto-dedupe; retry only with explicit allow_repeat.
_MUTATING_TOOLS = frozenset({
    "perception_session_start",
    "perception_session_end",
    "perception_execute_script",
    "perception_execute_actions",
    "perception_verify",
    "perception_integrate_component",
    "perception_inspiration_collect",
    "perception_resource_search",
    "perception_build_design_snapshot",
    "perception_design_graph_refresh",
    "perception_state_save",
    "perception_state_restore",
})


@dataclass
class SafeToolRegistry:
    safe_tools: frozenset[str] = field(default_factory=lambda: _SAFE_TOOLS)
    mutating_tools: frozenset[str] = field(default_factory=lambda: _MUTATING_TOOLS)

    def is_safe(self, tool: str) -> bool:
        if tool in self.mutating_tools:
            return False
        if tool in self.safe_tools:
            return True
        return tool.startswith("perception_coordinator_")

    def allows_auto_dedupe(self, tool: str) -> bool:
        return self.is_safe(tool)

    def allows_retry(self, tool: str, *, allow_repeat: bool = False) -> bool:
        if allow_repeat:
            return True
        return self.is_safe(tool)
