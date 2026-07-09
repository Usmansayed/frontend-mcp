"""Frontend Perception MCP server — host agent is the brain; this is the runtime."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any

os.environ.setdefault("BROWSER_USE_LOGGING_LEVEL", "warning")
os.environ.setdefault("BROWSER_USE_SETUP_LOGGING", "false")

logger = logging.getLogger(__name__)

try:
    import mcp.server.stdio
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    types = None  # type: ignore

from .handlers import (
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
    handle_full_diagnosis,
    handle_health,
    handle_navigate,
    handle_navigate_and_observe,
    handle_network_clear,
    handle_network_get,
    handle_observe,
    handle_probe_form,
    handle_probe_guards,
    handle_session_end,
    handle_session_start,
    handle_state_list,
    handle_state_restore,
    handle_state_save,
    handle_verify,
)
from .instructions import MCP_INSTRUCTIONS
from .resources import list_resources, read_resource
from navigation.core.scan_registry import ScanRegistry
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.visual.visual_response import envelope_to_mcp_contents


HandlerFn = Callable[..., Awaitable[dict[str, Any]]]


class PerceptionMCPServer:
    def __init__(self) -> None:
        if not MCP_AVAILABLE:
            raise RuntimeError("mcp package not installed. pip install mcp")
        self._store = SessionStore()
        self._scans = ScanRegistry()
        self._server = Server("frontend-perception")
        self._dispatch: dict[str, HandlerFn] = self._build_dispatch()

        @self._server.list_tools()
        async def list_tools() -> list[types.Tool]:
            return perception_tools(types)

        @self._server.list_resources()
        async def list_resources_handler() -> list[types.Resource]:
            return [
                types.Resource(
                    uri=item["uri"],
                    name=item["name"],
                    description=item["description"],
                    mimeType=item["mimeType"],
                )
                for item in list_resources(self._scans)
            ]

        @self._server.read_resource()
        async def read_resource_handler(uri: str) -> types.TextResourceContents | types.BlobResourceContents:
            uri_str = str(uri)
            mime, payload, is_blob = read_resource(uri_str, self._scans)
            if is_blob:
                return types.BlobResourceContents(uri=uri_str, mimeType=mime, blob=payload)
            return types.TextResourceContents(uri=uri_str, mimeType=mime, text=payload)

        @self._server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[Any]:
            args = arguments or {}
            try:
                handler = self._dispatch.get(name)
                if handler is None:
                    result = {
                        "contract_version": "1.0",
                        "tool": name,
                        "ok": False,
                        "error": f"unknown tool: {name}",
                        "data": {},
                    }
                else:
                    result = await handler(args)
            except Exception as exc:
                logger.exception("tool %s failed", name)
                result = {
                    "contract_version": "1.0",
                    "tool": name,
                    "ok": False,
                    "error": str(exc),
                    "data": {},
                }
            return envelope_to_mcp_contents(result, types)

    def _build_dispatch(self) -> dict[str, HandlerFn]:
        store = self._store
        scans = self._scans

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

        return {
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
        }

    async def run(self) -> None:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="frontend-perception",
                    server_version="0.11.0",
                    capabilities=self._server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                    instructions=MCP_INSTRUCTIONS,
                ),
            )


async def async_main() -> None:
    if not MCP_AVAILABLE:
        print("Install MCP: pip install mcp", file=sys.stderr)
        raise SystemExit(1)
    server = PerceptionMCPServer()
    try:
        await server.run()
    finally:
        await server._store.end_all()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
