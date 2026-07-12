"""Contract v1.0 envelope shape checks (T0 unit).

These tests validate the envelope contract without spawning the MCP server
or requiring a sandbox — they exercise ``make_envelope`` and confirm that
tool registrations, dispatch keys, and handler mappings all agree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.core.envelope import CONTRACT_VERSION, make_envelope
from navigation.mcp.server import PerceptionMCPServer
from navigation.mcp.tools import perception_tools


class _StubToolType:
    def __init__(self, name: str, description: str, inputSchema: dict) -> None:
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class _StubTypes:
    Tool = _StubToolType


@pytest.mark.unit
def test_envelope_default_shape() -> None:
    env = make_envelope("perception_health")
    assert env["contract_version"] == CONTRACT_VERSION == "1.0"
    assert env["tool"] == "perception_health"
    assert env["ok"] is True
    assert env["error"] is None
    assert env["degraded"] == []
    assert env["data"] == {}


@pytest.mark.unit
def test_envelope_error_shape() -> None:
    env = make_envelope("perception_verify", ok=False, error="bad_input")
    assert env["ok"] is False
    assert env["error"] == "bad_input"


@pytest.mark.unit
def test_envelope_degraded_is_copied() -> None:
    source = ["lighthouse_unavailable"]
    env = make_envelope("perception_audit_mode", degraded=source)
    source.append("other")
    assert env["degraded"] == ["lighthouse_unavailable"], "degraded must be defensively copied"


@pytest.mark.unit
def test_perception_tools_are_all_named_perception_() -> None:
    tools = perception_tools(_StubTypes)
    assert tools, "expected at least one tool"
    for tool in tools:
        assert tool.name.startswith("perception_"), f"tool {tool.name!r} lacks perception_ prefix"
        assert isinstance(tool.inputSchema, dict), tool.name
        assert tool.description, f"tool {tool.name!r} has empty description"


@pytest.mark.unit
def test_tool_names_are_unique() -> None:
    tools = perception_tools(_StubTypes)
    names = [t.name for t in tools]
    duplicates = [n for n in set(names) if names.count(n) > 1]
    assert not duplicates, f"duplicate tool names: {duplicates}"


@pytest.mark.unit
def test_dispatch_and_tools_agree() -> None:
    """Every registered tool schema must have a dispatch handler, and vice versa."""
    server = PerceptionMCPServer()
    dispatch_keys = set(server._runtime.registry.handlers.keys())
    tool_names = {t.name for t in perception_tools(_StubTypes)}

    missing_dispatch = tool_names - dispatch_keys
    orphan_dispatch = dispatch_keys - tool_names

    assert not missing_dispatch, (
        f"tool schemas without a dispatch handler: {sorted(missing_dispatch)}"
    )
    assert not orphan_dispatch, (
        f"dispatch handlers without a tool schema (orphans): {sorted(orphan_dispatch)}"
    )


@pytest.mark.unit
def test_expected_tool_count_at_least_66() -> None:
    tools = perception_tools(_StubTypes)
    assert len(tools) >= 66, f"tool count regressed: {len(tools)}"
