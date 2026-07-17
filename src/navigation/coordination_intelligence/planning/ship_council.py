"""Ship Council — post-draft, ROI-ranked ship challenges via design_review ship mode."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel
from navigation.coordination_intelligence.planning.decision_ledger import (
    apply_dispositions,
    is_signal_suppressed,
    load_ledger,
    save_ledger,
    upsert_challenge_entry,
    validate_accept_reason,
)

MAX_CHALLENGES = 5
PREFER_CHALLENGES = 4
ROI_HIGH_CUT = 0.45

SEVERITY_WEIGHT = {
    "blocking": 1.0,
    "major": 0.85,
    "minor": 0.4,
    "advisory": 0.15,
}

INFLUENCE_WEIGHT = {
    "structural": 1.0,
    "balanced": 0.9,
    "minimal": 0.35,
    "maintenance": 0.25,
}

SIGNAL_TEMPLATES: dict[str, dict[str, Any]] = {
    "nav_not_sticky": {
        "decision": "Navigation",
        "question": "Sidebar scrolls with content. Is this intentional for a productivity dashboard?",
        "why_it_matters": "Persistent navigation reduces context switching on data-heavy surfaces.",
        "owner": "agent",
        "default_action": "revise",
        "base_severity": "major",
        "visual_improvement": 0.88,
    },
    "narrow_centered_main": {
        "decision": "Layout",
        "question": "Main content uses a centered marketing-width layout. Should this be a full product settings or dashboard shell?",
        "why_it_matters": "Product settings and dashboards usually use full-width shells for density and scan efficiency.",
        "owner": "agent",
        "default_action": "revise",
        "base_severity": "major",
        "visual_improvement": 0.9,
    },
    "equal_weight_kpi_cluster": {
        "decision": "Information Hierarchy",
        "question": "Multiple KPI or card regions share equal visual weight. Should one metric become the dominant focal point?",
        "why_it_matters": "Equal weight flattens scanning; users miss the primary business signal.",
        "owner": "agent",
        "default_action": "revise",
        "base_severity": "major",
        "visual_improvement": 0.92,
    },
    "theme_not_coupled": {
        "decision": "Theme Coupling",
        "question": "Hard-coded colors dominate over theme tokens. Should palette follow light/dark theme variables?",
        "why_it_matters": "Uncoupled colors break theme switching and erode design-system consistency.",
        "owner": "agent",
        "default_action": "revise",
        "base_severity": "major",
        "visual_improvement": 0.86,
    },
    "responsive_breakage": {
        "decision": "Responsive Structure",
        "question": "Layout overflow or horizontal scroll detected. Should primary chrome collapse cleanly on smaller viewports?",
        "why_it_matters": "Broken responsive structure hides navigation and KPIs on laptops and tablets.",
        "owner": "agent",
        "default_action": "revise",
        "base_severity": "blocking",
        "visual_improvement": 0.84,
    },
    "dashboard_composition": {
        "decision": "Dashboard Composition",
        "question": "Dashboard sections compete for attention without a clear primary job. Should composition be simplified?",
        "why_it_matters": "Unclear section jobs increase cognitive load and slow task completion.",
        "owner": "agent",
        "default_action": "revise",
        "base_severity": "major",
        "visual_improvement": 0.87,
    },
    "spec_drift_major": {
        "decision": "Reference Conformance",
        "question": "Live UI materially diverges from the bound reference Spec. Should this drift be revised before ship?",
        "why_it_matters": "Unreviewed Spec drift often reintroduces hierarchy and spacing regressions.",
        "owner": "agent",
        "default_action": "revise",
        "base_severity": "major",
        "visual_improvement": 0.8,
    },
    "hierarchy_dense_ui": {
        "decision": "Composition",
        "question": "Interactive density is high with competing focal points. Should secondary actions be de-emphasized?",
        "why_it_matters": "Too many equal-weight controls slow decision-making on dashboard surfaces.",
        "owner": "agent",
        "default_action": "revise",
        "base_severity": "minor",
        "visual_improvement": 0.55,
    },
    "brand_direction": {
        "decision": "Visual Identity",
        "question": "Color and typography choices may reflect brand positioning. Should this direction be confirmed?",
        "why_it_matters": "Brand and visual identity tradeoffs require product or stakeholder alignment.",
        "owner": "user",
        "default_action": "ask_user",
        "base_severity": "major",
        "visual_improvement": 0.7,
    },
}

FRAMING = (
    "You're about to ship this frontend. "
    "Here are the highest-ROI decisions we'd challenge before approving release."
)


def should_skip_ship_council(
    *,
    influence_level: str,
    task_scope: str,
    polish_saturation: str = "none",
) -> bool:
    if influence_level in ("minimal", "maintenance"):
        return True
    if task_scope in ("hotfix", "surgical", "debug"):
        return True
    if polish_saturation == "hard":
        return False
    return False


def should_recommend_ship_mode(psm: ProjectSituationModel, strategy: dict[str, Any]) -> bool:
    influence = str(strategy.get("influence_level") or "")
    if influence not in ("structural", "balanced"):
        return False
    if not psm.artifacts.snapshot_id:
        return False
    if psm.episode.verification_status != "passed":
        return False
    gate = strategy.get("implementation_gate") or {}
    if gate.get("state") == "blocked":
        return False
    disc_scope = str(strategy.get("task_scope") or "")
    if disc_scope in ("hotfix", "surgical", "debug"):
        return False
    return True


def _roi_band(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= ROI_HIGH_CUT:
        return "medium"
    return "low"


def _lifecycle_weight(psm: ProjectSituationModel) -> float:
    weight = 0.65
    if psm.episode.verification_status == "passed":
        weight = 1.0
    saturation = str(psm.episode.retry_counters.get("polish_saturation") or "none")
    if saturation == "hard":
        weight *= 0.55
    elif saturation == "soft":
        weight *= 0.8
    return weight


def _strategy_weight(signal: str, strategy: dict[str, Any]) -> float:
    influence = str(strategy.get("influence_level") or "balanced")
    base = INFLUENCE_WEIGHT.get(influence, 0.7)
    unresolved = {
        str(d.get("decision_id") or ""): float(d.get("impact_weight") or 0.5)
        for d in (strategy.get("unresolved_decisions") or [])
    }
    for decision_id, impact in unresolved.items():
        if decision_id and decision_id in signal:
            return min(1.0, base + impact * 0.25)
    return base


def compute_roi_score(
    *,
    severity: str,
    strategy: dict[str, Any],
    psm: ProjectSituationModel,
    specdiff_magnitude: float,
    visual_improvement: float,
    signal: str,
) -> float:
    raw = (
        SEVERITY_WEIGHT.get(severity, 0.5)
        * _strategy_weight(signal, strategy)
        * _lifecycle_weight(psm)
        * max(min(specdiff_magnitude, 1.0), 0.1)
        * max(min(visual_improvement, 1.0), 0.1)
    )
    return round(min(1.0, raw), 4)


def _snapshot_dict(snapshot: Any) -> dict[str, Any]:
    if hasattr(snapshot, "to_dict"):
        return snapshot.to_dict()
    return dict(snapshot or {})


def _collect_snapshot_signals(snapshot: Any) -> list[dict[str, Any]]:
    snap = _snapshot_dict(snapshot)
    layout = snap.get("layout") or {}
    hierarchy = snap.get("hierarchy") or {}
    colors = snap.get("colors") or {}
    tokens = snap.get("design_tokens") or {}
    signals: list[dict[str, Any]] = []

    overflow = list(layout.get("overflow_issues") or [])
    visual = layout.get("visual_insights") or {}
    blocking = list(visual.get("blocking") or [])
    if overflow or blocking or any(
        i.get("kind") == "horizontal_overflow" for i in (visual.get("issues") or [])
    ):
        signals.append({
            "signal": "responsive_breakage",
            "severity": "blocking",
            "specdiff_magnitude": 0.95,
            "evidence_refs": ["snapshot:layout.overflow"],
        })

    token_ratio = float(colors.get("token_backed_ratio") or tokens.get("token_backed_ratio") or 1.0)
    if token_ratio < 0.45:
        signals.append({
            "signal": "theme_not_coupled",
            "severity": "major",
            "specdiff_magnitude": max(0.5, 1.0 - token_ratio),
            "evidence_refs": ["snapshot:colors.token_backed_ratio"],
        })

    prominence = list(hierarchy.get("prominence_scores") or [])
    if len(prominence) >= 3:
        values = [float(p.get("score") or p.get("prominence") or 0) for p in prominence]
        if values and (max(values) - min(values)) < 0.12:
            signals.append({
                "signal": "equal_weight_kpi_cluster",
                "severity": "major",
                "specdiff_magnitude": 0.75,
                "evidence_refs": ["snapshot:hierarchy.prominence_scores"],
            })

    regions = list(layout.get("regions") or [])
    nav_regions = [
        r for r in regions
        if str(r.get("role") or r.get("label") or "").lower() in {"nav", "sidebar", "aside", "navigation"}
    ]
    if nav_regions and not any(
        str(r.get("position") or r.get("style", {}).get("position") or "").lower() in {"fixed", "sticky"}
        for r in nav_regions
    ):
        signals.append({
            "signal": "nav_not_sticky",
            "severity": "major",
            "specdiff_magnitude": 0.7,
            "evidence_refs": ["snapshot:layout.regions"],
        })

    for region in regions:
        width = region.get("width_ratio") or region.get("width_pct")
        centered = bool(region.get("centered")) or str(region.get("layout_pattern") or "") == "marketing_centered"
        role = str(region.get("role") or region.get("label") or "").lower()
        if centered and (width is None or float(width) <= 0.72) and role in {"main", "content", "settings"}:
            signals.append({
                "signal": "narrow_centered_main",
                "severity": "major",
                "specdiff_magnitude": 0.82,
                "evidence_refs": ["snapshot:layout.regions"],
            })
            break

    if len(regions) >= 6:
        signals.append({
            "signal": "dashboard_composition",
            "severity": "major",
            "specdiff_magnitude": min(1.0, len(regions) / 10.0),
            "evidence_refs": ["snapshot:layout.regions"],
        })

    return signals


def _collect_specdiff_signals(engineering_delta: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not engineering_delta:
        return []
    signals: list[dict[str, Any]] = []
    for item in (engineering_delta.get("top_by_impact") or [])[:12]:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "major")
        if severity not in ("blocking", "major", "minor"):
            continue
        magnitude = float(item.get("impact_weight") or 0.5)
        kind = str(item.get("kind") or item.get("decision_id") or "").lower()
        detail = str(item.get("detail") or "")
        signal = "spec_drift_major"
        if "hierarchy" in kind or "kpi" in detail.lower():
            signal = "equal_weight_kpi_cluster"
        elif "layout" in kind or "width" in detail.lower() or "center" in detail.lower():
            signal = "narrow_centered_main"
        elif "nav" in kind or "sidebar" in detail.lower():
            signal = "nav_not_sticky"
        elif "color" in kind or "theme" in kind or "token" in detail.lower():
            signal = "theme_not_coupled"
        signals.append({
            "signal": signal,
            "severity": severity,
            "specdiff_magnitude": magnitude,
            "evidence_refs": [f"specdiff:{item.get('decision_id') or kind}"],
        })
    return signals


def _collect_finding_signals(findings: list[Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for finding in findings:
        if hasattr(finding, "to_dict"):
            f = finding.to_dict()
        elif isinstance(finding, dict):
            f = finding
        else:
            continue
        severity = str(f.get("severity") or "minor")
        if severity not in ("blocking", "major", "minor"):
            continue
        category = str(f.get("category") or "").lower()
        fid = str(f.get("id") or "")
        signal = "dashboard_composition"
        if category == "hierarchy" or "hierarchy" in fid:
            signal = "equal_weight_kpi_cluster" if "dense" not in fid else "hierarchy_dense_ui"
        elif category == "layout" or "overflow" in fid:
            signal = "responsive_breakage"
        elif category == "navigation":
            signal = "nav_not_sticky"
        elif category == "color":
            signal = "theme_not_coupled"
        elif category == "typography" and severity == "major":
            signal = "brand_direction"
        signals.append({
            "signal": signal,
            "severity": severity,
            "specdiff_magnitude": 0.65 if severity == "major" else 0.45,
            "evidence_refs": [f"design_review:{fid or category}"],
        })
    return signals


def _collect_revision_gate_signals(revision_gate: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not revision_gate or not revision_gate.get("revision_required"):
        return []
    drifts = list(revision_gate.get("blocking_drifts") or revision_gate.get("drifts") or [])
    if not drifts:
        return [{
            "signal": "spec_drift_major",
            "severity": "major",
            "specdiff_magnitude": 0.85,
            "evidence_refs": ["spec_revision_gate:revision_required"],
        }]
    return []


def _merge_signal_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for cand in candidates:
        signal = str(cand.get("signal") or "")
        if not signal:
            continue
        existing = merged.get(signal)
        if not existing:
            merged[signal] = dict(cand)
            continue
        existing["specdiff_magnitude"] = max(
            float(existing.get("specdiff_magnitude") or 0),
            float(cand.get("specdiff_magnitude") or 0),
        )
        sev_rank = {"blocking": 3, "major": 2, "minor": 1, "advisory": 0}
        if sev_rank.get(str(cand.get("severity")), 0) > sev_rank.get(str(existing.get("severity")), 0):
            existing["severity"] = cand.get("severity")
        refs = list(existing.get("evidence_refs") or [])
        for ref in cand.get("evidence_refs") or []:
            if ref not in refs:
                refs.append(ref)
        existing["evidence_refs"] = refs
    return list(merged.values())


def _materialize_challenge(
    cand: dict[str, Any],
    *,
    strategy: dict[str, Any],
    psm: ProjectSituationModel,
) -> dict[str, Any] | None:
    signal = str(cand.get("signal") or "")
    template = SIGNAL_TEMPLATES.get(signal)
    if not template:
        return None
    severity = str(cand.get("severity") or template.get("base_severity") or "major")
    roi_score = compute_roi_score(
        severity=severity,
        strategy=strategy,
        psm=psm,
        specdiff_magnitude=float(cand.get("specdiff_magnitude") or 0.5),
        visual_improvement=float(template.get("visual_improvement") or 0.5),
        signal=signal,
    )
    return {
        "decision_id": signal,
        "signal": signal,
        "decision": template["decision"],
        "question": template["question"],
        "why_it_matters": template["why_it_matters"],
        "severity": severity,
        "expected_roi": _roi_band(roi_score),
        "roi_score": roi_score,
        "default_action": template["default_action"],
        "owner": template["owner"],
        "evidence_refs": list(cand.get("evidence_refs") or []),
        "phase": "challenge",
        "disposition": None,
    }


def build_ship_council(
    *,
    psm: ProjectSituationModel,
    strategy: dict[str, Any],
    snapshot: Any,
    engineering_delta: dict[str, Any] | None,
    revision_gate: dict[str, Any] | None,
    findings: list[Any],
    dispositions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    influence = str(strategy.get("influence_level") or "balanced")
    task_scope = str(strategy.get("task_scope") or "")
    polish_saturation = str(psm.episode.retry_counters.get("polish_saturation") or "none")

    ledger = load_ledger(psm)
    rejected_dispositions: list[dict[str, Any]] = []
    if dispositions:
        _, rejected_dispositions = apply_dispositions(ledger, dispositions)

    if should_skip_ship_council(
        influence_level=influence,
        task_scope=task_scope,
        polish_saturation=polish_saturation,
    ):
        save_ledger(psm, ledger)
        return {
            "mode": "ship",
            "framing": FRAMING,
            "challenges": [],
            "ranked_roi": [],
            "ship_gate": {
                "state": "skipped",
                "open_high_roi": 0,
                "council_clear": True,
            },
            "ship_summary": _build_ship_summary(ledger, challenges_raised=0, open_high_roi=0),
            "decision_ledger": ledger,
            "rejected_dispositions": rejected_dispositions,
            "skipped_reason": f"influence={influence}, task_scope={task_scope}",
        }

    candidates = _merge_signal_candidates(
        _collect_snapshot_signals(snapshot)
        + _collect_specdiff_signals(engineering_delta)
        + _collect_finding_signals(findings)
        + _collect_revision_gate_signals(revision_gate)
    )

    challenges: list[dict[str, Any]] = []
    for cand in candidates:
        signal = str(cand.get("signal") or "")
        if is_signal_suppressed(ledger, signal):
            continue
        challenge = _materialize_challenge(cand, strategy=strategy, psm=psm)
        if not challenge:
            continue
        if challenge["roi_score"] < ROI_HIGH_CUT and challenge["severity"] not in ("blocking",):
            continue
        challenges.append(challenge)

    challenges.sort(key=lambda c: (-float(c["roi_score"]), c["signal"]))
    max_count = 2 if polish_saturation == "hard" else MAX_CHALLENGES
    if len(challenges) > max_count:
        challenges = challenges[:max_count]
    elif len(challenges) > PREFER_CHALLENGES and polish_saturation == "soft":
        challenges = challenges[:PREFER_CHALLENGES]

    ranked_roi = [
        {"decision": c["decision"], "roi_score": c["roi_score"]}
        for c in challenges
    ]

    open_challenges = [
        c for c in challenges
        if (ledger.get("entries") or {}).get(c["signal"], {}).get("phase") != "closed"
    ]
    awaiting_user = any(
        (ledger.get("entries") or {}).get(c["signal"], {}).get("disposition") == "ask_user"
        for c in challenges
    )

    for challenge in challenges:
        upsert_challenge_entry(ledger, challenge)

    if not challenges:
        gate_state = "clear"
        council_clear = True
    elif awaiting_user:
        gate_state = "awaiting_user"
        council_clear = False
    elif open_challenges:
        gate_state = "challenge"
        council_clear = False
    else:
        gate_state = "clear"
        council_clear = True

    open_high = [
        c for c in open_challenges
        if c.get("expected_roi") == "high"
    ]

    ship_summary = None
    if council_clear or polish_saturation == "hard":
        ship_summary = _build_ship_summary(
            ledger,
            challenges_raised=len(challenges),
            open_high_roi=len(open_high),
        )

    save_ledger(psm, ledger)

    return {
        "mode": "ship",
        "framing": FRAMING,
        "challenges": challenges,
        "ranked_roi": ranked_roi,
        "ship_gate": {
            "state": gate_state,
            "open_high_roi": len(open_high),
            "council_clear": council_clear,
        },
        "ship_summary": ship_summary,
        "decision_ledger": ledger,
        "rejected_dispositions": rejected_dispositions,
    }


def _build_ship_summary(
    ledger: dict[str, Any],
    *,
    challenges_raised: int,
    open_high_roi: int,
) -> dict[str, Any]:
    stats = ledger.get("session_stats") or {}
    revised = int(stats.get("revised") or 0)
    accepted = int(stats.get("accepted") or 0)
    asked_user = int(stats.get("asked_user") or 0)
    total = max(challenges_raised, revised + accepted + asked_user)

    if open_high_roi == 0 and total > 0:
        improvement = "high" if revised >= accepted else "medium"
        confidence = round(min(0.98, 0.72 + (revised * 0.06) + (accepted * 0.04)), 2)
    elif total == 0:
        improvement = "low"
        confidence = 0.85
    else:
        improvement = "medium"
        confidence = round(max(0.35, 0.75 - open_high_roi * 0.08), 2)

    return {
        "challenges_raised": total,
        "revised": revised,
        "accepted": accepted,
        "asked_user": asked_user,
        "estimated_ui_improvement": improvement,
        "ship_confidence": confidence,
    }


def ship_council_hint(strategy: dict[str, Any], psm: ProjectSituationModel) -> dict[str, Any] | None:
    if not should_recommend_ship_mode(psm, strategy):
        return None
    return {
        "capability": "design_review",
        "mode": "ship",
        "resource": "perception://ship-council",
        "reason": "Post-verify draft exists; run Ship Council before claiming done.",
    }
