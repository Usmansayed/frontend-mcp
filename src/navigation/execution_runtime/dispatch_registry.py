"""Dispatch registry — shared tool name → handler map for MCP and execution runtime."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.mcp.coordination_handlers import (
    handle_coordinator_apply_envelope,
    handle_coordinator_briefing,
    handle_coordinator_episode_start,
)
from navigation.mcp.design_intelligence_handlers import (
    handle_build_design_snapshot,
    handle_consistency_assess,
    handle_consistency_audit,
    handle_consistency_propose_fix,
    handle_consistency_review,
    handle_design_graph_refresh,
    handle_design_graph_summary,
    handle_design_knowledge_query,
    handle_design_review,
)
from navigation.mcp.handlers import (
    handle_auth_gate,
    handle_audit_accessibility,
    handle_audit_best_practices,
    handle_audit_mode,
    handle_audit_performance,
    handle_audit_seo,
    handle_code_context,
    handle_console_clear,
    handle_console_get,
    handle_debug_mode,
    handle_detect_framework,
    handle_diff,
    handle_execute_actions,
    handle_execute_script,
    handle_flow_describe,
    handle_framework_docs,
    handle_figma_connect,
    handle_figma_context,
    handle_figma_status,
    handle_full_diagnosis,
    handle_health,
    handle_inspiration_collect,
    handle_inspiration_discover,
    handle_inspiration_session_end,
    handle_integrate_component,
    handle_navigate,
    handle_navigate_and_observe,
    handle_network_clear,
    handle_network_get,
    handle_observe,
    handle_plan_component_search,
    handle_probe_form,
    handle_probe_guards,
    handle_resource_animation_search,
    handle_resource_avatar_search,
    handle_resource_font_search,
    handle_resource_icon_search,
    handle_resource_illustration_search,
    handle_resource_license_check,
    handle_resource_logo_search,
    handle_resource_observe_bridge,
    handle_resource_pattern_search,
    handle_resource_photo_search,
    handle_resource_preview,
    handle_resource_search,
    handle_resource_session_end,
    handle_search_components,
    handle_select_component_foundation,
    handle_seo_audit,
    handle_seo_connect,
    handle_seo_query,
    handle_seo_status,
    handle_seo_verify,
    handle_session_end,
    handle_session_start,
    handle_state_list,
    handle_state_restore,
    handle_state_save,
    handle_verify,
)
from navigation.visual_browser_intelligence.browser.session_store import SessionStore

HandlerFn = Callable[..., Awaitable[dict[str, Any]]]


class DispatchRegistry:
    """Maps perception_* tool names to async handler callables."""

    def __init__(self, handlers: dict[str, HandlerFn]) -> None:
        self._handlers = dict(handlers)

    @property
    def handlers(self) -> dict[str, HandlerFn]:
        return self._handlers

    def get(self, tool_name: str) -> HandlerFn | None:
        return self._handlers.get(tool_name)

    def tool_names(self) -> list[str]:
        return sorted(self._handlers.keys())

    @classmethod
    def build(
        cls,
        store: SessionStore,
        scans: ScanRegistry,
        snapshots: SnapshotRegistry,
    ) -> DispatchRegistry:
        async def health(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_health(args)

        async def session_start(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_session_start(store, args)

        async def session_end(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_session_end(store, args)

        async def navigate(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_navigate(store, args)

        async def navigate_and_observe(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_navigate_and_observe(store, scans, args)

        async def observe(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_observe(store, scans, args)

        async def execute_script(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_execute_script(store, scans, args)

        async def execute_actions(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_execute_actions(store, scans, args)

        async def verify(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_verify(store, scans, args)

        async def diff(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_diff(scans, args)

        async def auth_gate(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_auth_gate(store, args)

        async def probe_form(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_probe_form(store, args)

        async def probe_guards(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_probe_guards(store, args)

        async def state_save(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_state_save(store, args)

        async def state_restore(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_state_restore(store, args)

        async def state_list(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_state_list(store, args)

        async def flow_describe(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_flow_describe(args)

        async def code_context(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_code_context(args)

        async def console_get(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_console_get(store, args)

        async def console_clear(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_console_clear(store, args)

        async def network_get(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_network_get(store, args)

        async def network_clear(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_network_clear(store, args)

        async def audit_accessibility(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_audit_accessibility(store, args)

        async def audit_performance(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_audit_performance(store, args)

        async def audit_seo(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_audit_seo(store, args)

        async def audit_best_practices(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_audit_best_practices(store, args)

        async def full_diagnosis(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_full_diagnosis(store, scans, args)

        async def debug_mode(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_debug_mode(store, scans, args)

        async def audit_mode(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_audit_mode(store, scans, args)

        async def detect_framework(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_detect_framework(args)

        async def framework_docs(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_framework_docs(args)

        async def search_components(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_search_components(args)

        async def plan_component_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_plan_component_search(args)

        async def select_component_foundation(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_select_component_foundation(args)

        async def integrate_component(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_integrate_component(args)

        async def inspiration_discover(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_inspiration_discover(args)

        async def inspiration_collect(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_inspiration_collect(args)

        async def inspiration_session_end(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_inspiration_session_end(args)

        async def resource_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_search(args)

        async def resource_preview(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_preview(args)

        async def resource_session_end(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_session_end(args)

        async def resource_icon_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_icon_search(args)

        async def resource_font_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_font_search(args)

        async def resource_logo_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_logo_search(args)

        async def resource_photo_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_photo_search(args)

        async def resource_avatar_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_avatar_search(args)

        async def resource_illustration_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_illustration_search(args)

        async def resource_pattern_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_pattern_search(args)

        async def resource_animation_search(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_animation_search(args)

        async def resource_license_check(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_license_check(args)

        async def resource_observe_bridge(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_resource_observe_bridge(scans, args)

        async def seo_status(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_seo_status(args)

        async def seo_connect(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_seo_connect(args)

        async def seo_audit(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_seo_audit(scans, args)

        async def seo_query(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_seo_query(args)

        async def seo_verify(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_seo_verify(scans, args)

        async def figma_status(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_figma_status(args)

        async def figma_connect(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_figma_connect(args)

        async def figma_context(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_figma_context(args)

        async def build_design_snapshot(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_build_design_snapshot(store, scans, snapshots, args)

        async def design_review(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_design_review(store, scans, snapshots, args)

        async def consistency_review(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_consistency_review(store, scans, snapshots, args)

        async def consistency_audit(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_consistency_audit(store, scans, snapshots, args)

        async def design_knowledge_query(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_design_knowledge_query(args)

        async def design_graph_summary(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_design_graph_summary(args)

        async def design_graph_refresh(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_design_graph_refresh(store, scans, snapshots, args)

        async def consistency_assess(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_consistency_assess(args)

        async def consistency_propose_fix(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_consistency_propose_fix(args)

        async def coordinator_episode_start(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_coordinator_episode_start(args)

        async def coordinator_apply_envelope(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_coordinator_apply_envelope(args)

        async def coordinator_briefing(args: dict[str, Any]) -> dict[str, Any]:
            return await handle_coordinator_briefing(args)

        handlers: dict[str, HandlerFn] = {
            "perception_health": health,
            "perception_session_start": session_start,
            "perception_session_end": session_end,
            "perception_navigate": navigate,
            "perception_navigate_and_observe": navigate_and_observe,
            "perception_observe": observe,
            "perception_execute_script": execute_script,
            "perception_execute_actions": execute_actions,
            "perception_verify": verify,
            "perception_diff": diff,
            "perception_auth_gate": auth_gate,
            "perception_probe_form": probe_form,
            "perception_probe_guards": probe_guards,
            "perception_state_save": state_save,
            "perception_state_restore": state_restore,
            "perception_state_list": state_list,
            "perception_flow_describe": flow_describe,
            "perception_code_context": code_context,
            "perception_console_get": console_get,
            "perception_console_clear": console_clear,
            "perception_network_get": network_get,
            "perception_network_clear": network_clear,
            "perception_audit_accessibility": audit_accessibility,
            "perception_audit_performance": audit_performance,
            "perception_audit_seo": audit_seo,
            "perception_audit_best_practices": audit_best_practices,
            "perception_full_diagnosis": full_diagnosis,
            "perception_debug_mode": debug_mode,
            "perception_audit_mode": audit_mode,
            "perception_detect_framework": detect_framework,
            "perception_framework_docs": framework_docs,
            "perception_search_components": search_components,
            "perception_plan_component_search": plan_component_search,
            "perception_select_component_foundation": select_component_foundation,
            "perception_integrate_component": integrate_component,
            "perception_inspiration_discover": inspiration_discover,
            "perception_inspiration_collect": inspiration_collect,
            "perception_inspiration_session_end": inspiration_session_end,
            "perception_resource_search": resource_search,
            "perception_resource_preview": resource_preview,
            "perception_resource_session_end": resource_session_end,
            "perception_resource_icon_search": resource_icon_search,
            "perception_resource_font_search": resource_font_search,
            "perception_resource_logo_search": resource_logo_search,
            "perception_resource_photo_search": resource_photo_search,
            "perception_resource_avatar_search": resource_avatar_search,
            "perception_resource_illustration_search": resource_illustration_search,
            "perception_resource_pattern_search": resource_pattern_search,
            "perception_resource_animation_search": resource_animation_search,
            "perception_resource_license_check": resource_license_check,
            "perception_resource_observe_bridge": resource_observe_bridge,
            "perception_seo_status": seo_status,
            "perception_seo_connect": seo_connect,
            "perception_seo_audit": seo_audit,
            "perception_seo_query": seo_query,
            "perception_seo_verify": seo_verify,
            "perception_figma_status": figma_status,
            "perception_figma_connect": figma_connect,
            "perception_figma_context": figma_context,
            "perception_build_design_snapshot": build_design_snapshot,
            "perception_design_review": design_review,
            "perception_consistency_review": consistency_review,
            "perception_consistency_audit": consistency_audit,
            "perception_design_knowledge_query": design_knowledge_query,
            "perception_design_graph_summary": design_graph_summary,
            "perception_design_graph_refresh": design_graph_refresh,
            "perception_consistency_assess": consistency_assess,
            "perception_consistency_propose_fix": consistency_propose_fix,
            "perception_coordinator_episode_start": coordinator_episode_start,
            "perception_coordinator_apply_envelope": coordinator_apply_envelope,
            "perception_coordinator_briefing": coordinator_briefing,
        }
        return cls(handlers)
