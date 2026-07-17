"""Tests for `frontend-mcp install rules`."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.cli.install_rules import (
    AGENT_TOOLS,
    BEGIN,
    END,
    load_rule_body,
    write_rules_for_tool,
)
from navigation.cli.main import main as cli_main


@pytest.mark.unit
def test_top_six_agent_tools() -> None:
    assert len(AGENT_TOOLS) == 6
    keys = [t.key for t in AGENT_TOOLS]
    assert keys == ["cursor", "claude", "copilot", "opencode", "codex", "windsurf"]


@pytest.mark.unit
def test_packaged_rule_template_loads() -> None:
    body = load_rule_body()
    assert "Session order" in body
    assert "perception_health" in body
    assert "Done ladder" in body


@pytest.mark.unit
def test_write_cursor_rules(tmp_path: Path) -> None:
    path = write_rules_for_tool("cursor", root=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path.name.endswith(".mdc")
    assert "alwaysApply: true" in text
    assert "Session order" in text


@pytest.mark.unit
def test_write_claude_and_copilot_merge(tmp_path: Path) -> None:
    claude = write_rules_for_tool("claude", root=tmp_path)
    assert "perception_session_start" in claude.read_text(encoding="utf-8")

    copilot = tmp_path / ".github" / "copilot-instructions.md"
    copilot.parent.mkdir(parents=True)
    copilot.write_text("Existing team notes.\n", encoding="utf-8")
    path = write_rules_for_tool("copilot", root=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "Existing team notes." in text
    assert BEGIN in text and END in text
    assert text.count(BEGIN) == 1

    write_rules_for_tool("copilot", root=tmp_path)
    text2 = path.read_text(encoding="utf-8")
    assert text2.count(BEGIN) == 1
    assert "Existing team notes." in text2


@pytest.mark.unit
def test_cli_install_rules_with_tool_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        cli_main(["install", "rules", "--tool", "cursor"])
    assert exc.value.code == 0
    assert (tmp_path / ".cursor" / "rules" / "frontend-perception-mcp.mdc").is_file()
