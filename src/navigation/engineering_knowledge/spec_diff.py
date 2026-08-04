"""SpecDiff — deterministic delta between two FrontendEngineeringSpecs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from navigation.engineering_knowledge.catalog import catalog_by_id
from navigation.engineering_knowledge.models import EngineeringDecision, FrontendEngineeringSpec


@dataclass(slots=True)
class SpecDeltaItem:
    decision_id: str
    kind: str  # appeared | missing | value_drift | status_change | enum_mismatch
    from_value: Any = None
    to_value: Any = None
    from_status: str | None = None
    to_status: str | None = None
    severity: str = "minor"  # blocking | major | minor | advisory
    importance: str = "medium"
    impact_weight: float = 0.5
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "kind": self.kind,
            "from_value": self.from_value,
            "to_value": self.to_value,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "severity": self.severity,
            "importance": self.importance,
            "impact_weight": round(float(self.impact_weight), 4),
            "detail": self.detail,
        }


@dataclass(slots=True)
class EngineeringDelta:
    reference_source: str
    current_source: str
    items: list[SpecDeltaItem] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ranked = sorted(self.items, key=lambda i: (-i.impact_weight, i.decision_id))
        return {
            "reference_source": self.reference_source,
            "current_source": self.current_source,
            "items": [i.to_dict() for i in ranked],
            "summary": dict(self.summary),
            "top_by_impact": [i.to_dict() for i in ranked[:12]],
        }


_NUMERIC_DRIFT = {
    "layout.sidebar_width_px": 8.0,
    "layout.content_max_width_px": 40.0,
    "layout.header_height_px": 8.0,
    "spacing.base_unit_px": 0.0,  # any change matters
    "spacing.section_gap_px": 8.0,
    "spacing.card_gap_px": 4.0,
    "type.body_size_px": 1.0,
    "type.line_height_ratio": 0.1,
    "density.score": 0.15,
}


def diff_specs(
    reference: FrontendEngineeringSpec,
    current: FrontendEngineeringSpec,
) -> EngineeringDelta:
    """Compare decision values/statuses for V1 catalog IDs only."""
    catalog = catalog_by_id()
    items: list[SpecDeltaItem] = []
    all_ids = set(reference.decisions) | set(current.decisions) | set(catalog)

    for did in sorted(all_ids):
        if did not in catalog and did not in reference.decisions and did not in current.decisions:
            continue
        ref = reference.decision(did)
        cur = current.decision(did)
        meta = catalog.get(did)
        importance = (ref or cur or EngineeringDecision(did)).importance
        impact = (ref or cur or EngineeringDecision(did)).impact_weight
        if meta:
            importance = meta.importance
            impact = meta.impact_weight

        if ref is None and cur is not None and cur.status != "unresolved":
            items.append(
                SpecDeltaItem(
                    decision_id=did,
                    kind="appeared",
                    to_value=cur.value,
                    to_status=cur.status,
                    severity=_severity(impact, "appeared"),
                    importance=importance,
                    impact_weight=impact,
                    detail="Decision present in current Spec only.",
                )
            )
            continue
        if cur is None and ref is not None and ref.status != "unresolved":
            items.append(
                SpecDeltaItem(
                    decision_id=did,
                    kind="missing",
                    from_value=ref.value,
                    from_status=ref.status,
                    severity=_severity(impact, "missing"),
                    importance=importance,
                    impact_weight=impact,
                    detail="Decision present in reference Spec only.",
                )
            )
            continue
        if ref is None or cur is None:
            continue

        if ref.status != cur.status:
            items.append(
                SpecDeltaItem(
                    decision_id=did,
                    kind="status_change",
                    from_value=ref.value,
                    to_value=cur.value,
                    from_status=ref.status,
                    to_status=cur.status,
                    severity=_severity(impact, "status"),
                    importance=importance,
                    impact_weight=impact,
                    detail=f"Status {ref.status} → {cur.status}.",
                )
            )

        if not _values_equivalent(ref.value, cur.value):
            kind = "value_drift"
            if isinstance(ref.value, str) and isinstance(cur.value, str):
                kind = "enum_mismatch"
            if not _numeric_within_tolerance(did, ref.value, cur.value):
                items.append(
                    SpecDeltaItem(
                        decision_id=did,
                        kind=kind,
                        from_value=ref.value,
                        to_value=cur.value,
                        from_status=ref.status,
                        to_status=cur.status,
                        severity=_severity(impact, "drift"),
                        importance=importance,
                        impact_weight=impact,
                        detail=f"Value changed: {ref.value!r} → {cur.value!r}.",
                    )
                )

    major = sum(1 for i in items if i.severity in ("blocking", "major"))
    return EngineeringDelta(
        reference_source=reference.source_kind,
        current_source=current.source_kind,
        items=items,
        summary={
            "delta_count": len(items),
            "major_or_blocking": major,
            "impact_weighted_score": round(
                sum(i.impact_weight for i in items if i.severity in ("blocking", "major")),
                3,
            ),
        },
    )


def _severity(impact: float, kind: str) -> str:
    if impact >= 0.9:
        return "blocking" if kind in ("missing", "drift", "enum_mismatch") else "major"
    if impact >= 0.75:
        return "major"
    if impact >= 0.55:
        return "minor"
    return "advisory"


def _values_equivalent(a: Any, b: Any) -> bool:
    if a == b:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-6
    if isinstance(a, list) and isinstance(b, list):
        return [str(x) for x in a] == [str(x) for x in b]
    return str(a) == str(b)


def _numeric_within_tolerance(decision_id: str, a: Any, b: Any) -> bool:
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return False
    tol = _NUMERIC_DRIFT.get(decision_id)
    if tol is None:
        return False
    return abs(float(a) - float(b)) <= tol
