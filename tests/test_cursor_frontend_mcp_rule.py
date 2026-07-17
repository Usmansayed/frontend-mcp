"""Keep the Cursor rule dense and bootstrap-forcing (same-size, high-ROI surface)."""
from __future__ import annotations

from pathlib import Path

import pytest

RULE = Path(__file__).resolve().parents[1] / ".cursor" / "rules" / "frontend-perception-mcp.mdc"

REQUIRED = (
    "Session order",
    "Failure mode",
    "perception://getting-started",
    "perception_health",
    "perception_session_start",
    "implementation_gate",
    "data.verified",
    "advancement_eligible",
    "section_checklist_required",
    "ship_council_required",
    "Done ladder",
    "perception_design_review(mode=\"ship\")",
    "one at a time",
    "Full UI first, MCP only at the end",
    "ok=true` + `data.verified=false` = **fail**",
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
    # Front-load: session order before the long situation table
    assert text.index("Session order") < text.index("Situation → minimum evidence")
