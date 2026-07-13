"""Background SEO audit job runner."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from navigation.seo_intelligence.jobs.models import SeoAuditJobStatus
from navigation.seo_intelligence.jobs.store import SeoAuditJobStore, get_job_store
from navigation.seo_intelligence.models import SeoAuditRequest
from navigation.seo_intelligence.planning.modes import parse_audit_mode
from navigation.seo_intelligence.planning.orchestrator import SeoAuditOrchestrator

if TYPE_CHECKING:
    from navigation.core.scan_registry import ScanRegistry

logger = logging.getLogger(__name__)

_running_tasks: dict[str, asyncio.Task[None]] = {}


def _request_from_dict(raw: dict[str, Any]) -> SeoAuditRequest:
    mode_raw = raw.get("mode")
    mode = parse_audit_mode(str(mode_raw)) if mode_raw else None
    return SeoAuditRequest(
        website_url=str(raw.get("website_url") or ""),
        property_url=str(raw.get("property_url") or ""),
        repo_root=str(raw.get("repo_root") or ""),
        scan_id=str(raw.get("scan_id") or ""),
        ga4_property_id=str(raw.get("ga4_property_id") or ""),
        bing_site_url=str(raw.get("bing_site_url") or ""),
        providers=[str(p) for p in (raw.get("providers") or []) if p],
        intents=[str(i) for i in (raw.get("intents") or []) if i],
        mode=mode,
        include_cross_analysis=bool(raw.get("include_cross_analysis", True)),
        include_recommendations=bool(raw.get("include_recommendations", True)),
        include_ai_visibility=bool(raw.get("include_ai_visibility", True)),
        ai_reasoning=raw.get("ai_reasoning") if "ai_reasoning" in raw else None,
    )


class SeoAuditJobRunner:
    def __init__(
        self,
        *,
        store: SeoAuditJobStore | None = None,
        scan_registry: ScanRegistry | None = None,
    ) -> None:
        self._store = store or get_job_store()
        self._scan_registry = scan_registry

    def start(self, request: SeoAuditRequest, *, setup_notes: list[str] | None = None) -> str:
        job = self._store.create(request.to_dict())
        if setup_notes:
            job.degraded.extend(setup_notes)
            self._store.save(job)
        task = asyncio.create_task(self._run(job.audit_job_id), name=f"seo-audit-{job.audit_job_id}")
        _running_tasks[job.audit_job_id] = task
        task.add_done_callback(lambda _t: _running_tasks.pop(job.audit_job_id, None))
        return job.audit_job_id

    async def _run(self, audit_job_id: str) -> None:
        job = self._store.get(audit_job_id)
        if job is None:
            return
        if job.cancel_requested:
            job.status = SeoAuditJobStatus.CANCELLED
            self._store.save(job)
            return

        orchestrator = SeoAuditOrchestrator(scan_registry=self._scan_registry)

        def _on_progress(phase: str, pct: int, message: str, **extra: Any) -> None:
            j = self._store.get(audit_job_id)
            if j is None or j.cancel_requested:
                return
            j.progress.pct = pct
            j.progress.message = message
            if phase == "collecting":
                j.status = SeoAuditJobStatus.COLLECTING
            elif phase == "analyzing":
                j.status = SeoAuditJobStatus.ANALYZING
            elif phase == "bootstrapping":
                j.status = SeoAuditJobStatus.BOOTSTRAPPING
            if extra.get("current_provider"):
                j.progress.current_provider = str(extra["current_provider"])
            if extra.get("completed_providers") is not None:
                j.progress.completed_providers = list(extra["completed_providers"])
            if extra.get("pending_providers") is not None:
                j.progress.pending_providers = list(extra["pending_providers"])
            self._store.save(j)

        def _on_evidence(item: dict[str, Any]) -> None:
            self._store.append_evidence_delta(audit_job_id, item)

        def _is_cancelled() -> bool:
            j = self._store.get(audit_job_id)
            return bool(j and j.cancel_requested)

        try:
            request = _request_from_dict(job.request)
            result = await orchestrator.audit(
                request,
                progress_callback=_on_progress,
                is_cancelled=_is_cancelled,
                on_evidence=_on_evidence,
            )
            j = self._store.get(audit_job_id)
            if j is None:
                return
            if j.cancel_requested:
                j.status = SeoAuditJobStatus.CANCELLED
                j.error = "cancelled_by_user"
                self._store.save(j)
                return
            j.status = SeoAuditJobStatus.COMPLETED
            j.latest_audit_id = result.audit_id
            j.seo_audit = result.to_dict()
            j.degraded = sorted(set(j.degraded + list(result.degraded)))
            j.progress.pct = 100
            j.progress.message = "completed"
            self._store.save(j)
        except asyncio.CancelledError:
            j = self._store.get(audit_job_id)
            if j is not None:
                j.status = SeoAuditJobStatus.CANCELLED
                j.error = "task_cancelled"
                self._store.save(j)
            raise
        except Exception as exc:
            logger.exception("seo audit job %s failed", audit_job_id)
            j = self._store.get(audit_job_id)
            if j is not None:
                j.status = SeoAuditJobStatus.FAILED
                j.error = str(exc)
                self._store.save(j)
