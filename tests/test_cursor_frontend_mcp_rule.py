"""Keep the tracked Cursor rule dense and bootstrap-forcing (same-size, high-ROI surface).

The installable / documented rule lives at docs/cursor-rules/frontend-mcp.mdc
(copied into .cursor by the CLI). Assert against the tracked file so CI and
isolated worktrees do not depend on an ignored local .cursor copy.
"""
from __future__ import annotations

from pathlib import Path

import pytest

RULE = Path(__file__).resolve().parents[1] / "docs" / "cursor-rules" / "frontend-mcp.mdc"

REQUIRED = (
    "perception://getting-started",
    "perception_health",
    "perception_session_start",
    "implementation_gate",
    "data.verified",
    "advancement_eligible",
    "section_checklist_required",
    "ship_council_required",
    "Done ladder",
    'perception_design_review(mode="ship")',
    "one at a time",
    "Do not code a full UI first and use MCP only at the end",
    "Situation → minimum evidence",
)

# Keep roughly the established footprint — grow only with clear ROI.
MAX_LINES = 220
MIN_LINES = 140


@pytest.mark.unit
def test_frontend_mcp_rule_is_effective_bootstrap_contract() -> None:
    text = RULE.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert MIN_LINES <= len(lines) <= MAX_LINES, f"unexpected size: {len(lines)} lines"
    for phrase in REQUIRED:
        assert phrase in text, f"rule missing effective phrase: {phrase}"
    # Front-load: pre-code gate before the long situation table
    assert text.index("Pre-code gate") < text.index("Situation → minimum evidence")
