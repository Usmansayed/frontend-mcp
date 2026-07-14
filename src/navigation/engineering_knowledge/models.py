"""Frontend Engineering Spec models — decision-centric host contract (V1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


STATUSES = ("resolved", "partial", "unresolved", "conflicting", "not_applicable")
IMPORTANCE = ("critical", "high", "medium", "low")

# Frozen V1 groups — do not expand until A/B justifies.
V1_GROUPS = (
    "layout",
    "information_hierarchy",
    "navigation_model",
    "spacing_system",
    "typography",
    "color_system",
    "component_foundation",
    "visual_density",
)


@dataclass(slots=True)
class EngineeringDecision:
    """One named engineering decision — rebuild contract unit."""

    decision_id: str
    status: str = "unresolved"
    value: Any = None
    unit: str | None = None
    confidence: float = 0.0
    importance: str = "medium"
    impact_weight: float = 0.5
    evidence: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    why: str = ""
    why_code: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_refs: list[str] = field(default_factory=list)
    group: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "group": self.group,
            "status": self.status,
            "value": self.value,
            "unit": self.unit,
            "confidence": round(float(self.confidence), 4),
            "importance": self.importance,
            "impact_weight": round(float(self.impact_weight), 4),
            "evidence": list(self.evidence),
            "constraints": dict(self.constraints),
            "why": self.why,
            "why_code": self.why_code,
            "provenance": dict(self.provenance),
            "raw_refs": list(self.raw_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EngineeringDecision:
        return cls(
            decision_id=str(data.get("decision_id") or ""),
            status=str(data.get("status") or "unresolved"),
            value=data.get("value"),
            unit=data.get("unit"),
            confidence=float(data.get("confidence") or 0.0),
            importance=str(data.get("importance") or "medium"),
            impact_weight=float(data.get("impact_weight") or 0.5),
            evidence=list(data.get("evidence") or []),
            constraints=dict(data.get("constraints") or {}),
            why=str(data.get("why") or ""),
            why_code=str(data.get("why_code") or ""),
            provenance=dict(data.get("provenance") or {}),
            raw_refs=list(data.get("raw_refs") or []),
            group=str(data.get("group") or ""),
        )


@dataclass(slots=True)
class FrontendEngineeringSpec:
    """Canonical engineering decision contract for host rebuild + coordinator."""

    schema_version: str = "1.0"
    catalog_version: str = "v1_pareto"
    source_kind: str = "unknown"
    compiled_at: str = field(default_factory=_utc_now)
    provenance: dict[str, Any] = field(default_factory=dict)
    decisions: dict[str, EngineeringDecision] = field(default_factory=dict)
    degraded: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        by_group: dict[str, dict[str, Any]] = {g: {} for g in V1_GROUPS}
        unresolved: list[dict[str, Any]] = []
        resolved_count = 0
        for did, dec in sorted(
            self.decisions.items(),
            key=lambda item: (-item[1].impact_weight, item[0]),
        ):
            blob = dec.to_dict()
            group = dec.group if dec.group in by_group else "layout"
            by_group.setdefault(group, {})[did] = blob
            if dec.status in ("unresolved", "partial", "conflicting"):
                unresolved.append(blob)
            elif dec.status == "resolved":
                resolved_count += 1

        return {
            "schema_version": self.schema_version,
            "catalog_version": self.catalog_version,
            "source_kind": self.source_kind,
            "compiled_at": self.compiled_at,
            "provenance": dict(self.provenance),
            "groups": by_group,
            "decisions": {k: v.to_dict() for k, v in self.decisions.items()},
            "coverage": {
                "total": len(self.decisions),
                "resolved": resolved_count,
                "unresolved_or_partial": len(unresolved),
                "coverage_ratio": round(
                    resolved_count / max(len(self.decisions), 1), 4
                ),
            },
            "unresolved_by_impact": unresolved[:16],
            "degraded": list(self.degraded),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FrontendEngineeringSpec:
        decisions_raw = data.get("decisions") or {}
        decisions = {
            k: EngineeringDecision.from_dict(v) if isinstance(v, dict) else v
            for k, v in decisions_raw.items()
        }
        return cls(
            schema_version=str(data.get("schema_version") or "1.0"),
            catalog_version=str(data.get("catalog_version") or "v1_pareto"),
            source_kind=str(data.get("source_kind") or "unknown"),
            compiled_at=str(data.get("compiled_at") or _utc_now()),
            provenance=dict(data.get("provenance") or {}),
            decisions=decisions,
            degraded=list(data.get("degraded") or []),
        )

    def decision(self, decision_id: str) -> EngineeringDecision | None:
        return self.decisions.get(decision_id)

    def unresolved_critical(self) -> list[EngineeringDecision]:
        out = [
            d
            for d in self.decisions.values()
            if d.status in ("unresolved", "partial", "conflicting")
            and d.importance in ("critical", "high")
        ]
        out.sort(key=lambda d: -d.impact_weight)
        return out
