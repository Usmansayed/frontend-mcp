"""Route design-reference evidence: redesign prefers measured snapshot over gallery."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel

# Live-app redesign / mockup: measure (or bind) before gallery inspiration.
SNAPSHOT_FIRST_SCOPES = frozenset({"redesign"})


def prefer_snapshot_first(task_scope: str | None) -> bool:
    return str(task_scope or "") in SNAPSHOT_FIRST_SCOPES


def snapshot_reference_paid(psm: ProjectSituationModel) -> bool:
    """True when a measured snapshot has progressed the design-reference decision."""
    outcome = (psm.evidence.capability_ledger or {}).get("design_snapshot") or {}
    status = str(outcome.get("status") or "")
    if status in ("failed", "noop"):
        return False
    if outcome.get("advancement_eligible") is True:
        return True
    return status in ("succeeded", "provisional")


def order_design_reference_capabilities(
    capabilities: list[str],
    *,
    task_scope: str | None,
    psm: ProjectSituationModel,
) -> list[str]:
    """Reorder resolving caps so redesign tips gate.next toward design_snapshot."""
    caps = [str(c) for c in capabilities if c]
    if not prefer_snapshot_first(task_scope):
        return caps
    if snapshot_reference_paid(psm):
        return caps
    if "design_snapshot" not in caps:
        return caps
    return ["design_snapshot", *[c for c in caps if c != "design_snapshot"]]


def design_reference_workflow_resource(
    *,
    task_scope: str | None,
    next_capability: str | None,
    psm: ProjectSituationModel | None = None,
) -> str | None:
    """Resource for design_reference — redesign/snapshot path uses redesign-workflow."""
    if next_capability == "design_snapshot":
        return "perception://redesign-workflow"
    if prefer_snapshot_first(task_scope) and psm is not None and not snapshot_reference_paid(psm):
        return "perception://redesign-workflow"
    if next_capability == "inspiration_workflow":
        return "perception://guide/inspiration"
    return None
