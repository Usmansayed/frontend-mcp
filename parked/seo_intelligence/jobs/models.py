"""SEO async audit job models."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SeoAuditJobStatus(str, Enum):
    QUEUED = "queued"
    BOOTSTRAPPING = "bootstrapping"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_JOB_STATUSES = frozenset(
    {
        SeoAuditJobStatus.COMPLETED,
        SeoAuditJobStatus.FAILED,
        SeoAuditJobStatus.CANCELLED,
    }
)


def new_audit_job_id() -> str:
    return f"audit_job_{uuid.uuid4().hex[:16]}"


@dataclass
class SeoAuditJobProgress:
    pct: int = 0
    current_provider: str = ""
    completed_providers: list[str] = field(default_factory=list)
    pending_providers: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pct": self.pct,
            "current_provider": self.current_provider,
            "completed_providers": list(self.completed_providers),
            "pending_providers": list(self.pending_providers),
            "message": self.message,
        }


@dataclass
class SeoAuditJob:
    audit_job_id: str
    status: SeoAuditJobStatus
    request: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    progress: SeoAuditJobProgress = field(default_factory=SeoAuditJobProgress)
    evidence_ids: list[str] = field(default_factory=list)
    evidence_seq: int = 0
    degraded: list[str] = field(default_factory=list)
    error: str | None = None
    latest_audit_id: str | None = None
    seo_audit: dict[str, Any] | None = None
    cancel_requested: bool = False
    poll_seq: int = 0

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_JOB_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_job_id": self.audit_job_id,
            "status": self.status.value,
            "terminal": self.terminal,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": self.progress.to_dict(),
            "evidence_ids": list(self.evidence_ids),
            "evidence_count": len(self.evidence_ids),
            "evidence_seq": self.evidence_seq,
            "degraded": list(self.degraded),
            "error": self.error,
            "latest_audit_id": self.latest_audit_id,
            "poll_interval_ms": 2000,
        }

    def poll_payload(self, *, since_evidence_seq: int = 0) -> dict[str, Any]:
        payload = self.to_dict()
        if since_evidence_seq > 0:
            payload["since_evidence_seq"] = since_evidence_seq
        return payload
