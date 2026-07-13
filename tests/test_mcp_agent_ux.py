"""Tests for MCP agent guidance and tool catalog."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.core.envelope import make_envelope
from navigation.mcp.agent_guidance import guidance_for_degraded, guidance_for_error
from navigation.mcp.tool_catalog import apply_tool_catalog, infer_group, group_summary
from navigation.mcp.tools import perception_tools


class _StubTool:
    def __init__(self, name: str, description: str, inputSchema: dict, **kwargs) -> None:
        self.name = name
        self.description = description
        self.inputSchema = inputSchema
        for k, v in kwargs.items():
            setattr(self, k, v)


class _StubTypes:
    Tool = _StubTool


@pytest.mark.unit
def test_guidance_for_session_error() -> None:
    g = guidance_for_error("session_id required")
    assert g and "session_start" in g[0]["agent_action"]


@pytest.mark.unit
def test_guidance_for_degraded_scan() -> None:
    g = guidance_for_degraded(["scan_id missing from prior observe"])
    assert g and "navigate_and_observe" in g[0]["agent_action"]


@pytest.mark.unit
def test_envelope_attaches_guidance_on_error() -> None:
    env = make_envelope("perception_verify", ok=False, error="session_id required")
    assert env.get("agent_guidance")
    assert any("session_start" in item["agent_action"] for item in env["agent_guidance"])


@pytest.mark.unit
def test_tool_groups_cover_all_tools() -> None:
    tools = perception_tools(_StubTypes)
    assert len(tools) >= 83
    for t in tools:
        assert infer_group(t.name), t.name
        assert t.description.startswith("["), t.name
        meta = getattr(t, "_meta", None)
        assert meta and meta.get("perception", {}).get("group"), t.name


@pytest.mark.unit
def test_tools_sorted_by_group() -> None:
    tools = perception_tools(_StubTypes)
    assert infer_group(tools[0].name) == "Session"
    summary = group_summary(tools)
    assert summary.get("Browser", 0) >= 5
    assert summary.get("Session", 0) >= 2
    assert len(summary) >= 8


@pytest.mark.unit
def test_schema_has_session_id_examples() -> None:
    tools = {t.name: t for t in perception_tools(_StubTypes)}
    schema = tools["perception_verify"].inputSchema
    sid = schema.get("properties", {}).get("session_id", {})
    assert sid.get("examples"), "session_id should have examples"
