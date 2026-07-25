"""Tests for frontend-mcp setup + methodology skill packaging."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.cli.setup import (
    agents_md_template,
    install_cursor_skill,
    main as setup_main,
)


@pytest.mark.unit
def test_skill_template_packaged() -> None:
    skill = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "navigation"
        / "cli"
        / "data"
        / "skills"
        / "frontend-engineering-with-perception"
        / "SKILL.md"
    )
    text = skill.read_text(encoding="utf-8")
    assert "frontend-engineering-with-perception" in text
    assert "agent_summary.coordinator" in text
    assert "Phase branches" in text
    assert "tool catalog" in text.lower() or "not a tool catalog" in text.lower()


@pytest.mark.unit
def test_install_cursor_skill_copies_skill_md(tmp_path: Path) -> None:
    dest = install_cursor_skill(dest_root=tmp_path)
    assert (dest / "SKILL.md").is_file()
    body = (dest / "SKILL.md").read_text(encoding="utf-8")
    assert "recommended_next" in body


@pytest.mark.unit
def test_setup_prints_mcp_json(capsys: pytest.CaptureFixture[str]) -> None:
    code = setup_main([])
    assert code == 0
    out = capsys.readouterr().out
    assert "mcpServers" in out
    assert "frontend-mcp" in out
    assert "session_start with intent" in out
    # Ensure printed block is valid JSON fragment when extracted
    start = out.index("{")
    end = out.index("}", start)
    # find matching end of mcp block — parse via line scan
    block_start = out.index('{\n  "mcpServers"')
    depth = 0
    i = block_start
    while i < len(out):
        if out[i] == "{":
            depth += 1
        elif out[i] == "}":
            depth -= 1
            if depth == 0:
                block = out[block_start : i + 1]
                parsed = json.loads(block)
                assert "frontend-mcp" in parsed["mcpServers"]
                break
        i += 1
    else:
        pytest.fail("mcp.json block not found")


@pytest.mark.unit
def test_agents_md_template_mentions_coordinator() -> None:
    text = agents_md_template()
    assert "coordinator" in text
    assert "intent" in text
