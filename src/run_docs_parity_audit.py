"""Docs parity audit (Wave 4 / gate G7).

Cross-checks that every tool defined in ``navigation.mcp.tools`` has:
- a dispatch handler in ``navigation.mcp.server``
- an entry in ``docs/tool_reference.md`` (by name match)
- if listed in ``AGENT_GUIDE.md`` sections, the name spelling matches

Emits ``artifacts/docs_parity/report.json`` and returns non-zero on drift.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT


TOOL_NAME_PATTERN = re.compile(r"\bperception_[a-z][a-z0-9]*(?:_[a-z][a-z0-9]*)*\b")


class _StubToolType:
    def __init__(self, name: str, description: str, inputSchema: dict) -> None:
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class _StubTypes:
    Tool = _StubToolType


def _read_tools_and_dispatch() -> tuple[list[str], set[str]]:
    from navigation.mcp.server import PerceptionMCPServer
    from navigation.mcp.tools import perception_tools

    tools = [t.name for t in perception_tools(_StubTypes)]
    server = PerceptionMCPServer()
    dispatch = set(server._runtime.registry.tool_names())
    return tools, dispatch


def _names_in_file(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return set(TOOL_NAME_PATTERN.findall(text))


def main() -> int:
    parser = argparse.ArgumentParser(description="Docs parity audit")
    parser.add_argument("--strict", action="store_true", help="Fail on any drift")
    args = parser.parse_args()

    tools, dispatch = _read_tools_and_dispatch()
    tool_names = set(tools)

    tool_reference = _names_in_file(ROOT / "docs" / "tool_reference.md")
    agent_guide = _names_in_file(ROOT / "src" / "navigation" / "mcp" / "AGENT_GUIDE.md")
    instructions = _names_in_file(ROOT / "src" / "navigation" / "mcp" / "instructions.py")

    missing_dispatch = sorted(tool_names - dispatch)
    orphan_dispatch = sorted(dispatch - tool_names)
    missing_from_reference = sorted(tool_names - tool_reference)
    unknown_in_reference = sorted(tool_reference - tool_names)
    unknown_in_agent_guide = sorted(agent_guide - tool_names)
    unknown_in_instructions = sorted(instructions - tool_names)

    report = {
        "suite": "docs_parity",
        "tool_count": len(tool_names),
        "dispatch_count": len(dispatch),
        "missing_dispatch": missing_dispatch,
        "orphan_dispatch": orphan_dispatch,
        "missing_from_reference": missing_from_reference,
        "unknown_in_reference": unknown_in_reference,
        "unknown_in_agent_guide": unknown_in_agent_guide,
        "unknown_in_instructions": unknown_in_instructions,
        "reference_coverage_pct": round(
            100.0 * len(tool_names & tool_reference) / max(1, len(tool_names)), 1
        ),
    }
    # Reference / instructions files legitimately mention data-payload fields
    # like ``perception_report`` and prefixes; only agent_guide is prose that
    # should not name non-existent tools. Missing-from-reference is a P3 gap
    # that only blocks under --strict.
    report["ok"] = (
        not missing_dispatch
        and not orphan_dispatch
        and not unknown_in_agent_guide
        and (not args.strict or not missing_from_reference)
    )

    out_dir = ROOT / "artifacts" / "docs_parity"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Docs parity: {'PASS' if report['ok'] else 'FAIL'}")
    print(f"  tools: {report['tool_count']}, dispatch: {report['dispatch_count']}")
    print(f"  reference coverage: {report['reference_coverage_pct']}%")
    for key in (
        "missing_dispatch",
        "orphan_dispatch",
        "missing_from_reference",
        "unknown_in_reference",
        "unknown_in_agent_guide",
        "unknown_in_instructions",
    ):
        items = report.get(key) or []
        if items:
            print(f"  {key}: {items}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
