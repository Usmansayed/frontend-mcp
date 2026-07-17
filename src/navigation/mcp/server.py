"""Frontend Perception MCP server — host agent is the brain; this is the runtime."""

from __future__ import annotations



import asyncio

import logging

import os

import sys

from typing import Any



from navigation.core.env import load_project_env



load_project_env()



os.environ.setdefault("BROWSER_USE_LOGGING_LEVEL", "warning")

os.environ.setdefault("BROWSER_USE_SETUP_LOGGING", "false")



logger = logging.getLogger(__name__)



try:

    import mcp.server.stdio

    import mcp.types as types

    from mcp.server import NotificationOptions, Server

    from mcp.server.models import InitializationOptions
    from mcp.server.lowlevel.helper_types import ReadResourceContents



    MCP_AVAILABLE = True

except ImportError:

    MCP_AVAILABLE = False

    types = None  # type: ignore



from .instructions import MCP_INSTRUCTIONS

from .resources import list_resources, read_resource

from .tools import perception_tools

from navigation.core.scan_registry import ScanRegistry

from navigation.core.snapshot_registry import SnapshotRegistry

from navigation.execution_runtime.runtime import ExecutionRuntime, configure

from navigation.visual_browser_intelligence.browser.browser_session_manager import BrowserSessionManager
from navigation.visual_browser_intelligence.browser.session_store import SessionStore

from navigation.visual_browser_intelligence.visual.visual_response import envelope_to_mcp_contents





class PerceptionMCPServer:

    def __init__(self) -> None:

        if not MCP_AVAILABLE:

            raise RuntimeError("mcp package not installed. pip install mcp")

        self._browser_manager = BrowserSessionManager.get()
        self._store = SessionStore(manager=self._browser_manager)

        self._scans = ScanRegistry()

        self._snapshots = SnapshotRegistry()

        self._runtime = ExecutionRuntime(self._store, self._scans, self._snapshots)

        configure(self._runtime)

        self._server = Server("frontend-perception")



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



        @self._server.list_resource_templates()

        async def list_resource_templates_handler() -> list[types.ResourceTemplate]:
            return [
                types.ResourceTemplate(
                    uriTemplate="perception://scan/{scan_id}/{artifact}",
                    name="scan_artifact",
                    description="Observation artifacts for a scan (report, screenshots, HAR)",
                    mimeType="application/octet-stream",
                ),
            ]

        @self._server.read_resource()

        async def read_resource_handler(uri: str) -> list[ReadResourceContents]:
            uri_str = str(uri)
            mime, payload, is_blob = read_resource(uri_str, self._scans)
            if is_blob:
                import base64

                return [
                    ReadResourceContents(
                        content=base64.b64decode(payload),
                        mime_type=mime or "application/octet-stream",
                    )
                ]
            return [ReadResourceContents(content=payload, mime_type=mime or "text/plain")]



        @self._server.call_tool()

        async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[Any]:

            args = arguments or {}

            result = await self._runtime.execute_tool(name, args)

            return envelope_to_mcp_contents(result.envelope, types)



    async def run(self) -> None:

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):

            await self._server.run(

                read_stream,

                write_stream,

                InitializationOptions(

                    server_name="frontend-perception",

                    server_version="1.2.0.dev5",

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

    import asyncio

    from navigation.component_intelligence.providers.shadcn_ecosystem.catalog import warm_shadcn_catalog_cache

    await asyncio.to_thread(warm_shadcn_catalog_cache)

    server = PerceptionMCPServer()

    try:

        await server.run()

    finally:

        await server._store.end_all()

        from navigation.seo_intelligence.setup.companion_processes import shutdown_companions



        shutdown_companions()





def main() -> None:

    asyncio.run(async_main())





if __name__ == "__main__":

    main()


