"""Progressive methodology discovery through MCP resources and tool metadata."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.mcp.resources import list_resources, read_resource
from navigation.mcp.tools import perception_tools


EXPECTED_WORKFLOWS = {
    "perception://getting-started",
    "perception://frontend-methodology",
    "perception://design-workflow",
    "perception://redesign-workflow",
    "perception://bugfix-workflow",
    "perception://engineering-strategy",
    "perception://decision-ledger",
    "perception://verification-guide",
    "perception://browser-lifecycle",
    "perception://ship-council",
}


class _Tool:
    def __init__(self, name: str, description: str, inputSchema: dict, **_: object) -> None:
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class _Types:
    Tool = _Tool


@pytest.mark.unit
def test_focused_methodology_resources_list_and_read() -> None:
    listed = {item["uri"] for item in list_resources()}
    assert EXPECTED_WORKFLOWS <= listed
    for uri in EXPECTED_WORKFLOWS:
        mime, text, is_blob = read_resource(uri)
        assert mime == "text/markdown"
        assert is_blob is False
        assert "Use when" in text
        assert "Implementation boundary" in text


@pytest.mark.unit
def test_high_impact_tools_have_compact_methodology_contracts() -> None:
    tools = {tool.name: tool for tool in perception_tools(_Types)}
    high_impact = {
        "perception_health",
        "perception_session_start",
        "perception_verify",
        "perception_plan_component_search",
        "perception_select_component_foundation",
        "perception_inspiration_collect",
        "perception_figma_context",
        "perception_build_design_snapshot",
        "perception_design_review",
    }
    for name in high_impact:
        description = tools[name].description
        for label in ("Does:", "Use when:", "Returns:", "Next:"):
            assert label in description, f"{name} missing {label}"
        assert len(description) <= 700, f"{name} description is too long"
