"""Resolver contracts — shared types for resolve_* and validate_* tools."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class ResolverKind(str, Enum):
    ROUTE = "route"
    COMPONENT = "component"
    API_ENDPOINT = "api_endpoint"
    DESIGN_TOKEN = "design_token"
    LAYOUT = "layout"
    STATE_OWNER = "state_owner"


class ResolverStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    LOW_CONFIDENCE = "low_confidence"
    ERROR = "error"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass(slots=True)
class EvidenceRef:
    file: str = ""
    line: int | None = None
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
        }


@dataclass(slots=True)
class ResolverMatch:
    summary: str
    file_path: str
    symbol: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    route: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "file_path": self.file_path,
            "symbol": self.symbol,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "route": self.route,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class FallbackHint:
    strategy: Literal["validate_claim", "host_search", "correlate_live_only"]
    message: str
    suggested_tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "message": self.message,
            "suggested_tools": list(self.suggested_tools),
        }


@dataclass(slots=True)
class ResolverResult:
    ok: bool
    kind: ResolverKind
    status: ResolverStatus
    confidence: ConfidenceLevel
    matches: list[ResolverMatch] = field(default_factory=list)
    evidence: list[EvidenceRef] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)
    latency_ms: int = 0
    resolver_id: str = ""
    confidence_score: float = 0.0
    fallback: FallbackHint | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "kind": self.kind.value,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "confidence_score": self.confidence_score,
            "matches": [m.to_dict() for m in self.matches],
            "evidence": [e.to_dict() for e in self.evidence],
            "degraded": list(self.degraded),
            "latency_ms": self.latency_ms,
            "resolver_id": self.resolver_id,
            "fallback": self.fallback.to_dict() if self.fallback else None,
            "error": self.error,
        }


@dataclass(slots=True)
class ResolverQuery:
    kind: ResolverKind
    params: dict[str, Any] = field(default_factory=dict)
    hints: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    checks: list[CheckResult] = field(default_factory=list)
    mcp_resolve: ResolverResult | None = None
    normalized_match: ResolverMatch | None = None
    degraded: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "checks": [c.to_dict() for c in self.checks],
            "mcp_resolve": self.mcp_resolve.to_dict() if self.mcp_resolve else None,
            "normalized_match": (
                self.normalized_match.to_dict() if self.normalized_match else None
            ),
            "degraded": list(self.degraded),
        }
