"""Minimal Guide Lab MCP — resources only. Does NOT start production frontend-mcp."""
from __future__ import annotations

import asyncio
from pathlib import Path

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp import types

# evals/guide_lab lives at repo root relative to this file when installed editable
_REPO = Path(__file__).resolve().parents[3]
_LAB = _REPO / "evals" / "guide_lab"
_ARM_B = _LAB / "arms" / "arm_b_clean"
_ARM_A = _LAB / "arms" / "arm_a_large"


def _arm_resources(arm_dir: Path, prefix: str) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    if not arm_dir.is_dir():
        return items
    for path in sorted(arm_dir.glob("*.md")):
        uri = f"guide-lab://{prefix}/{path.stem}"
        items.append((uri, path.name, path.read_text(encoding="utf-8")))
    return items


def build_catalog() -> dict[str, tuple[str, str]]:
    """uri -> (title, body)."""
    cat: dict[str, tuple[str, str]] = {}
    for uri, title, body in _arm_resources(_ARM_B, "clean"):
        cat[uri] = (title, body)
    for uri, title, body in _arm_resources(_ARM_A, "large"):
        cat[uri] = (title, body)
    cat["guide-lab://readme"] = (
        "Guide Lab README",
        (_LAB / "README.md").read_text(encoding="utf-8")
        if (_LAB / "README.md").is_file()
        else "Guide Lab — isolated large vs clean guide experiment.",
    )
    return cat


def create_server() -> Server:
    server = Server("frontend-mcp-guide-lab")
    catalog = build_catalog()

    @server.list_resources()
    async def list_resources_handler() -> list[types.Resource]:
        return [
            types.Resource(
                uri=uri,
                name=title,
                description=f"Guide Lab ({uri})",
                mimeType="text/markdown",
            )
            for uri, (title, _) in catalog.items()
        ]

    @server.read_resource()
    async def read_resource_handler(uri: str) -> list[ReadResourceContents]:
        item = catalog.get(uri)
        if not item:
            raise ValueError(f"Unknown Guide Lab resource: {uri}")
        _title, body = item
        return [ReadResourceContents(content=body, mime_type="text/markdown")]

    return server


async def _run() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="frontend-mcp-guide-lab",
                server_version="0.1.0.dev0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
