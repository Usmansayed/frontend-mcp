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

from navigation.visual_browser_intelligence.browser.session_store import SessionStore

from navigation.visual_browser_intelligence.visual.visual_response import envelope_to_mcp_contents





class PerceptionMCPServer:

    def __init__(self) -> None:

        if not MCP_AVAILABLE:

            raise RuntimeError("mcp package not installed. pip install mcp")

        self._store = SessionStore()

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

            result = await self._runtime.execute_tool(name, args)

            return envelope_to_mcp_contents(result.envelope, types)



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

        from navigation.seo_intelligence.setup.companion_processes import shutdown_companions



        shutdown_companions()





def main() -> None:

    asyncio.run(async_main())





if __name__ == "__main__":

    main()


