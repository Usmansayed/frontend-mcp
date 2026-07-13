"""Persistent + in-memory SEO audit job store."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from navigation.seo_intelligence.jobs.models import SeoAuditJob, SeoAuditJobStatus, new_audit_job_id

DEFAULT_JOBS_DIR = Path(os.environ.get("SEO_JOBS_DIR", ".cache/seo_jobs"))


class SeoAuditJobStore:
    def __init__(self, *, root: Path | None = None) -> None:
        self._root = root or DEFAULT_JOBS_DIR
        self._jobs: dict[str, SeoAuditJob] = {}
        self._lock = threading.RLock()
        self._evidence_deltas: dict[str, list[dict[str, Any]]] = {}

    def create(self, request: dict[str, Any]) -> SeoAuditJob:
        job_id = new_audit_job_id()
        job = SeoAuditJob(
            audit_job_id=job_id,
            status=SeoAuditJobStatus.QUEUED,
            request=dict(request),
        )
        with self._lock:
            self._jobs[job_id] = job
            self._evidence_deltas[job_id] = []
            self._persist(job)
        return job

    def get(self, audit_job_id: str) -> SeoAuditJob | None:
        with self._lock:
            job = self._jobs.get(audit_job_id)
            if job is not None:
                return job
            path = self._path(audit_job_id)
            if not path.is_file():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            job = _job_from_dict(data)
            self._jobs[job_id] = job
            self._evidence_deltas.setdefault(job_id, [])
            return job

    def save(self, job: SeoAuditJob) -> None:
        job.updated_at = time.time()
        with self._lock:
            self._jobs[job.audit_job_id] = job
            self._persist(job)

    def append_evidence_delta(self, audit_job_id: str, item: dict[str, Any]) -> None:
        with self._lock:
            job = self.get(audit_job_id)
            if job is None:
                return
            eid = str(item.get("evidence_id") or "")
            if eid and eid not in job.evidence_ids:
                job.evidence_ids.append(eid)
            job.evidence_seq += 1
            self._evidence_deltas.setdefault(audit_job_id, []).append(item)
            self.save(job)

    def evidence_delta_since(self, audit_job_id: str, since_seq: int) -> list[dict[str, Any]]:
        with self._lock:
            _ = self.get(audit_job_id)
            deltas = self._evidence_deltas.get(audit_job_id) or []
            if since_seq <= 0:
                return list(deltas)
            return deltas[since_seq:]

    def request_cancel(self, audit_job_id: str) -> SeoAuditJob | None:
        job = self.get(audit_job_id)
        if job is None:
            return None
        job.cancel_requested = True
        if not job.terminal:
            job.status = SeoAuditJobStatus.CANCELLED
            job.error = "cancelled_by_user"
            job.progress.message = "cancelled"
        self.save(job)
        return job

    def _path(self, audit_job_id: str) -> Path:
        return self._root / f"{audit_job_id}.json"

    def _persist(self, job: SeoAuditJob) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        payload = job.to_dict()
        payload["request"] = job.request
        payload["seo_audit"] = job.seo_audit
        payload["cancel_requested"] = job.cancel_requested
        self._path(job.audit_job_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _job_from_dict(data: dict[str, Any]) -> SeoAuditJob:
    from navigation.seo_intelligence.jobs.models import SeoAuditJobProgress

    progress_raw = data.get("progress") or {}
    progress = SeoAuditJobProgress(
        pct=int(progress_raw.get("pct") or 0),
        current_provider=str(progress_raw.get("current_provider") or ""),
        completed_providers=list(progress_raw.get("completed_providers") or []),
        pending_providers=list(progress_raw.get("pending_providers") or []),
        message=str(progress_raw.get("message") or ""),
    )
    status_raw = str(data.get("status") or SeoAuditJobStatus.QUEUED.value)
    try:
        status = SeoAuditJobStatus(status_raw)
    except ValueError:
        status = SeoAuditJobStatus.FAILED
    return SeoAuditJob(
        audit_job_id=str(data.get("audit_job_id") or ""),
        status=status,
        request=dict(data.get("request") or {}),
        created_at=float(data.get("created_at") or time.time()),
        updated_at=float(data.get("updated_at") or time.time()),
        progress=progress,
        evidence_ids=list(data.get("evidence_ids") or []),
        evidence_seq=int(data.get("evidence_seq") or 0),
        degraded=list(data.get("degraded") or []),
        error=data.get("error"),
        latest_audit_id=data.get("latest_audit_id"),
        seo_audit=data.get("seo_audit"),
        cancel_requested=bool(data.get("cancel_requested")),
        poll_seq=int(data.get("poll_seq") or 0),
    )


_default_store: SeoAuditJobStore | None = None


def get_job_store() -> SeoAuditJobStore:
    global _default_store
    if _default_store is None:
        _default_store = SeoAuditJobStore()
    return _default_store
