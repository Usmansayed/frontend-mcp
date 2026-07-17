"""Contract tests for production-facing MCP bootstrap surfaces.

These catch regressions where agents skip MCP in real sessions because the
preamble / getting-started / tool metadata stopped demanding bootstrap.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.mcp.instructions import MCP_INSTRUCTIONS
from navigation.mcp.resources import read_resource
from navigation.mcp.tools import perception_tools


class _Tool:
    def __init__(self, name: str, description: str, inputSchema: dict, **_: object) -> None:
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class _Types:
    Tool = _Tool


REQUIRED_INSTRUCTION_PHRASES = (
    "PRODUCTION FAILURE MODE",
    "MANDATORY FIRST ACTIONS",
    "perception://getting-started",
    "perception_health",
    "perception_session_start",
    "implementation_gate",
    "data.verified=true",
    "Do NOT write a full viewport",
    "Skip-bootstrap is a hard fail",
)


@pytest.mark.unit
def test_mcp_instructions_demand_bootstrap_before_coding() -> None:
    text = MCP_INSTRUCTIONS
    for phrase in REQUIRED_INSTRUCTION_PHRASES:
        assert phrase in text, f"MCP_INSTRUCTIONS missing: {phrase}"


@pytest.mark.unit
def test_getting_started_is_production_first() -> None:
    mime, text, is_blob = read_resource("perception://getting-started")
    assert mime == "text/markdown"
    assert is_blob is False
    assert "Production rule" in text
    assert "perception_health" in text
    assert "perception_session_start" in text
    assert "false-green" in text.lower() or "End-of-task MCP" in text
    assert "data.verified=true" in text
    assert "Implementation boundary" in text


@pytest.mark.unit
def test_bootstrap_tools_forbid_end_of_task_only_usage() -> None:
    tools = {tool.name: tool for tool in perception_tools(_Types)}
    health = tools["perception_health"].description
    start = tools["perception_session_start"].description
    verify = tools["perception_verify"].description
    assert "FIRST call" in health or "before planning or coding" in health
    assert "never skip to end-of-task" in health.lower() or "end-of-task" in health
    assert "immediately after health" in start.lower() or "required before observe" in start
    assert "data.verified" in verify
    assert "Done ladder" in verify
    assert "skipped bootstrap" in verify.lower() or "never as a substitute" in verify.lower()
