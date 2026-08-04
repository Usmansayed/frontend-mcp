"""Episode Confidence — process completeness for agent/user (not a gate)."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.evidence_plan_status import (
    evidence_plan_coverage,
    get_plan_status_map,
)


def compile_episode_confidence(
    *,
    psm: ProjectSituationModel,
    evidence_plan: list[dict[str, Any]] | None = None,
    section_complete: bool = True,
    ship_clear: bool = False,
    residue_required: bool = False,
    snapshot_coverage: str | None = None,
    open_backlog_majors: int = 0,
    spec_bound: bool = False,
    episode_portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score = 0.45
    contributors: list[dict[str, Any]] = []

    def add(cid: str, delta: float, detail: str) -> None:
        nonlocal score
        score += delta
        contributors.append({"id": cid, "delta": round(delta, 3), "detail": detail})

    if psm.episode.verification_status == "passed":
        add("verify_passed", 0.12, "Page verify passed")
    if section_complete:
        add("sections_complete", 0.08, "Section checklist complete or not required")
    else:
        add("sections_open", -0.1, "Section checklist incomplete")
    if ship_clear:
        add("ship_clear", 0.15, "Ship Council clear")
    if spec_bound or bool(psm.artifacts.snapshot_id):
        if spec_bound:
            add("spec_bound", 0.12, "Reference Spec bound")
        else:
            add("snapshot_present", 0.05, "Design snapshot present")

    plan_cov = evidence_plan_coverage(psm, evidence_plan or [])
    portfolio = episode_portfolio or {}
    paid_n = len(portfolio.get("paid") or [])
    unpaid_n = len(portfolio.get("unpaid") or [])
    if paid_n + unpaid_n > 0:
        port_cov = paid_n / (paid_n + unpaid_n)
    else:
        port_cov = 1.0 if paid_n else plan_cov
    # Prefer the stronger signal so supersede/snapshot progress is visible.
    coverage = max(plan_cov, port_cov)
    add(
        "evidence_coverage",
        round(0.2 * coverage, 3),
        f"Evidence coverage {int(round(coverage * 100))}%",
    )
    if paid_n > 0:
        add(
            "portfolio_paid",
            round(min(0.12, 0.03 * paid_n), 3),
            f"{paid_n} intelligence family(ies) paid in episode",
        )

    if residue_required:
        add("residue_pending", -0.08, "Residue scan pending")
    if snapshot_coverage == "thin":
        add("thin_coverage", -0.1, "Snapshot coverage thin")
    elif snapshot_coverage == "full":
        add("full_coverage", 0.06, "Snapshot coverage full")
    if open_backlog_majors > 0:
        add(
            "open_backlog",
            -min(0.15, 0.04 * open_backlog_majors),
            f"{open_backlog_majors} high-ROI backlog item(s) open",
        )

    status = get_plan_status_map(psm)
    skipped = sum(
        1
        for entry in status.values()
        if isinstance(entry, dict) and entry.get("state") == "skipped"
    )
    if skipped:
        add("valid_skips", -0.02 * min(skipped, 3), f"{skipped} evidence item(s) skipped (valid reason)")

    score = max(0.0, min(1.0, score))
    if score < 0.55:
        band = "low"
    elif score < 0.8:
        band = "medium"
    else:
        band = "high"
    return {
        "score": round(score, 2),
        "band": band,
        "contributors": contributors,
    }
