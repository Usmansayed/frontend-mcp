"""Development insights via CDP — Tier A (blocking) + Tier B (advisory)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .cdp_hub import CDP_CONSOLE, CDP_EXCEPTION, CDP_LOADING_FAILED, CDP_REQUEST, CDP_RESPONSE
from .cdp_hub import DevInsightsHub
from .preflight import wait_until, wait_until_async

SLOW_REQUEST_MS = 2000
UI_ERROR_SELECTORS = ".error-text, .error, [role='alert'], .validation-error, .alert-danger, .banner-error"

_PRIORITY = {
    "exception": 100,
    "console_error": 90,
    "network_failure": 85,
    "console_warning": 40,
    "api_call": 30,
    "slow_request": 20,
}


def _get(params: Any, key: str, default: Any = None) -> Any:
    if params is None:
        return default
    if isinstance(params, dict):
        return params.get(key, default)
    return getattr(params, key, default)


def _remote_object_text(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, dict):
        if obj.get("value") is not None:
            return str(obj["value"])
        if obj.get("description"):
            return str(obj["description"])
        if obj.get("unserializableValue"):
            return str(obj["unserializableValue"])
    return str(obj)


def _format_console_message(params: Any) -> str:
    args = _get(params, "args") or []
    parts = [_remote_object_text(a) for a in args]
    return " ".join(p for p in parts if p).strip()


def _format_stack_trace(stack: Any) -> str:
    if not stack:
        return ""
    frames = _get(stack, "callFrames") or []
    lines: list[str] = []
    for fr in frames[:8]:
        if isinstance(fr, dict):
            fn = fr.get("functionName") or "<anonymous>"
            url = fr.get("url") or ""
            line = fr.get("lineNumber")
            lines.append(f"  at {fn} ({url}:{line})")
    return "\n".join(lines)


def _exception_message(details: Any) -> str:
    text = str(_get(details, "text") or "")
    exc = _get(details, "exception") or {}
    desc = str(_get(exc, "description") or "")
    if desc:
        return desc
    if text and text != "Uncaught":
        return text
    stack = _format_stack_trace(_get(details, "stackTrace"))
    if "Error:" in stack:
        for line in stack.splitlines():
            if "Error:" in line:
                return line.strip()
    return text or "exception"


def _is_api_url(url: str) -> bool:
    return "/api/" in url or url.rstrip("/").endswith("/api")


class _EntryStore:
    """Dedup by key; when full, drop lowest-priority entries first."""

    def __init__(self, max_entries: int) -> None:
        self.max_entries = max_entries
        self._items: dict[tuple[Any, ...], tuple[Any, int, int]] = {}

    def add(self, kind: str, key: tuple[Any, ...], item: Any) -> None:
        priority = _PRIORITY.get(kind, 0)
        if key in self._items:
            existing, pri, count = self._items[key]
            new_count = count + 1
            if hasattr(existing, "count"):
                existing.count = new_count
            self._items[key] = (existing, pri, new_count)
            return
        if len(self._items) >= self.max_entries:
            worst_key = min(self._items, key=lambda k: self._items[k][1])
            if priority <= self._items[worst_key][1]:
                return
            del self._items[worst_key]
        self._items[key] = (item, priority, 1)

    def values(self) -> list[Any]:
        ordered = sorted(self._items.values(), key=lambda t: -t[1])
        return [item for item, _pri, _count in ordered]


@dataclass(slots=True)
class ConsoleEntry:
    level: str
    text: str
    stack: str = ""
    source: str = "cdp"
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "text": self.text,
            "stack": self.stack,
            "source": self.source,
            "count": self.count,
        }


@dataclass(slots=True)
class ExceptionEntry:
    text: str
    url: str = ""
    line: int | None = None
    column: int | None = None
    stack: str = ""
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "url": self.url,
            "line": self.line,
            "column": self.column,
            "stack": self.stack,
            "count": self.count,
        }


@dataclass(slots=True)
class NetworkFailure:
    url: str
    method: str = ""
    status: int | None = None
    status_text: str = ""
    error_text: str = ""
    failed: bool = False
    canceled: bool = False
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "status_text": self.status_text,
            "error_text": self.error_text,
            "failed": self.failed,
            "canceled": self.canceled,
            "count": self.count,
        }


@dataclass(slots=True)
class ApiCallEntry:
    url: str
    method: str = ""
    status: int | None = None
    duration_ms: float | None = None
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "count": self.count,
        }


@dataclass(slots=True)
class SlowRequestEntry:
    url: str
    method: str = ""
    status: int | None = None
    duration_ms: float = 0.0
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "count": self.count,
        }


@dataclass(slots=True)
class PageMeta:
    title: str = ""
    ready_state: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "ready_state": self.ready_state}


@dataclass(slots=True)
class DevInsights:
    url: str = ""
    console_errors: list[ConsoleEntry] = field(default_factory=list)
    console_warnings: list[ConsoleEntry] = field(default_factory=list)
    exceptions: list[ExceptionEntry] = field(default_factory=list)
    network_failures: list[NetworkFailure] = field(default_factory=list)
    api_calls: list[ApiCallEntry] = field(default_factory=list)
    slow_requests: list[SlowRequestEntry] = field(default_factory=list)
    ui_errors: list[str] = field(default_factory=list)
    page_meta: PageMeta | None = None
    degraded: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.console_errors)

    @property
    def warn_count(self) -> int:
        return len(self.console_warnings)

    @property
    def exception_count(self) -> int:
        return len(self.exceptions)

    @property
    def network_failure_count(self) -> int:
        return len(self.network_failures)

    def blocking_issues(self) -> list[str]:
        issues: list[str] = []
        for e in self.console_errors:
            issues.append(f"Console error: {e.text}")
        for e in self.exceptions:
            issues.append(f"Uncaught exception: {e.text}")
        for n in self.network_failures:
            if n.failed:
                issues.append(f"Network failed: {n.url} ({n.error_text})")
            elif n.status is not None:
                issues.append(f"HTTP {n.status}: {n.url}")
        return issues

    def advisory_issues(self) -> list[str]:
        issues: list[str] = []
        for w in self.console_warnings:
            issues.append(f"Console warn: {w.text}")
        for call in self.api_calls:
            status = call.status if call.status is not None else "?"
            issues.append(f"API {call.method} {call.url} -> {status}")
        for slow in self.slow_requests:
            issues.append(f"Slow request ({slow.duration_ms:.0f}ms): {slow.method} {slow.url}")
        for msg in self.ui_errors:
            issues.append(f"UI error: {msg}")
        if self.page_meta and self.page_meta.ready_state != "complete":
            issues.append(f"Page not complete: readyState={self.page_meta.ready_state}")
        return issues

    def summary(self) -> dict[str, Any]:
        return {
            "error_count": self.error_count,
            "warn_count": self.warn_count,
            "exception_count": self.exception_count,
            "network_failure_count": self.network_failure_count,
            "api_call_count": len(self.api_calls),
            "slow_request_count": len(self.slow_requests),
            "ui_error_count": len(self.ui_errors),
            "degraded": list(self.degraded),
            "blocking_issues": self.blocking_issues()[:20],
            "advisory_issues": self.advisory_issues()[:20],
        }

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "url": self.url,
            "summary": self.summary(),
            "degraded": list(self.degraded),
            "console_errors": [e.to_dict() for e in self.console_errors],
            "console_warnings": [e.to_dict() for e in self.console_warnings],
            "exceptions": [e.to_dict() for e in self.exceptions],
            "network_failures": [n.to_dict() for n in self.network_failures],
            "api_calls": [a.to_dict() for a in self.api_calls],
            "slow_requests": [s.to_dict() for s in self.slow_requests],
            "ui_errors": list(self.ui_errors),
        }
        if self.page_meta is not None:
            out["page_meta"] = self.page_meta.to_dict()
        return out


class DevInsightsCollector:
    """Capture Tier A + Tier B CDP signals during a browser interaction window."""

    def __init__(self, *, max_entries: int = 50) -> None:
        self.max_entries = max_entries
        self._console_errors = _EntryStore(max_entries)
        self._console_warnings = _EntryStore(max_entries)
        self._exceptions = _EntryStore(max_entries)
        self._network_failures = _EntryStore(max_entries)
        self._api_calls = _EntryStore(max_entries)
        self._slow_requests = _EntryStore(max_entries)
        self._ui_errors: list[str] = []
        self._page_meta: PageMeta | None = None
        self._degraded: list[str] = []
        self._request_methods: dict[str, str] = {}
        self._request_urls: dict[str, str] = {}
        self._request_start: dict[str, float] = {}
        self._hub: DevInsightsHub | None = None
        self._started = False

    async def start(self, session: Any) -> None:
        if self._started:
            return
        self._hub = await DevInsightsHub.for_session(session)
        await self._hub.ensure_domains()
        if self._hub.network_error:
            self._degraded.append("network_cdp_unavailable")
        self._hub.attach(self)
        self._started = True

    async def snapshot_page_signals(self, session: Any) -> None:
        from .verification import evaluate_js

        meta = await evaluate_js(
            session,
            "({ title: document.title || '', readyState: document.readyState || '' })",
        )
        if isinstance(meta, dict):
            self._page_meta = PageMeta(
                title=str(meta.get("title") or ""),
                ready_state=str(meta.get("readyState") or ""),
            )
        else:
            self._degraded.append("page_meta_unavailable")

        ui_errors = await evaluate_js(
            session,
            f"""(() => {{
              const sel = {UI_ERROR_SELECTORS!r};
              const nodes = Array.from(document.querySelectorAll(sel));
              return [...new Set(nodes.map(n => (n.innerText || n.textContent || '').trim()).filter(Boolean))];
            }})()""",
        )
        if isinstance(ui_errors, list):
            self._ui_errors = [str(x) for x in ui_errors if x][: self.max_entries]
        else:
            self._degraded.append("ui_scan_unavailable")

    def stop(self, *, url: str = "") -> DevInsights:
        if self._started and self._hub is not None:
            self._hub.detach(self)
        self._started = False
        self._hub = None
        return DevInsights(
            url=url,
            console_errors=self._console_errors.values(),
            console_warnings=self._console_warnings.values(),
            exceptions=self._exceptions.values(),
            network_failures=self._network_failures.values(),
            api_calls=self._api_calls.values(),
            slow_requests=self._slow_requests.values(),
            ui_errors=list(self._ui_errors),
            page_meta=self._page_meta,
            degraded=list(self._degraded),
        )

    def _handle_cdp(self, method: str, params: Any, session_id: str | None = None) -> None:
        if method == CDP_CONSOLE:
            self._on_console(params)
        elif method == CDP_EXCEPTION:
            self._on_exception(params)
        elif method == CDP_REQUEST:
            self._on_request(params)
        elif method == CDP_RESPONSE:
            self._on_response(params)
        elif method == CDP_LOADING_FAILED:
            self._on_loading_failed(params)

    def _on_console(self, params: Any) -> None:
        level = str(_get(params, "type") or "")
        if level not in ("error", "warning"):
            return
        text = _format_console_message(params)
        stack = _format_stack_trace(_get(params, "stackTrace"))
        entry = ConsoleEntry(level=level, text=text, stack=stack)
        key = (level, text)
        if level == "error":
            self._console_errors.add("console_error", key, entry)
        else:
            self._console_warnings.add("console_warning", key, entry)

    def _on_exception(self, params: Any) -> None:
        details = _get(params, "exceptionDetails") or {}
        text = _exception_message(details)
        url = str(_get(details, "url") or "")
        line = _get(details, "lineNumber")
        col = _get(details, "columnNumber")
        stack = _format_stack_trace(_get(details, "stackTrace"))
        entry = ExceptionEntry(
            text=text,
            url=url,
            line=int(line) if line is not None else None,
            column=int(col) if col is not None else None,
            stack=stack,
        )
        self._exceptions.add("exception", (text, url, line), entry)

    def _on_request(self, params: Any) -> None:
        request_id = str(_get(params, "requestId") or "")
        req = _get(params, "request") or {}
        url = str(_get(req, "url") or "")
        method = str(_get(req, "method") or "")
        if request_id:
            if url:
                self._request_urls[request_id] = url
            if method:
                self._request_methods[request_id] = method
            self._request_start[request_id] = time.monotonic()

    def _record_response(self, request_id: str, url: str, status: int | None) -> None:
        start = self._request_start.pop(request_id, None)
        duration_ms = (time.monotonic() - start) * 1000 if start is not None else None
        method = self._request_methods.get(request_id, "")

        if duration_ms is not None and duration_ms >= SLOW_REQUEST_MS:
            entry = SlowRequestEntry(url=url, method=method, status=status, duration_ms=duration_ms)
            self._slow_requests.add("slow_request", (url, method), entry)

        if _is_api_url(url):
            entry = ApiCallEntry(url=url, method=method, status=status, duration_ms=duration_ms)
            self._api_calls.add("api_call", (url, method, status), entry)

    def _on_response(self, params: Any) -> None:
        response = _get(params, "response") or {}
        status = _get(response, "status")
        request_id = str(_get(params, "requestId") or "")
        url = str(_get(response, "url") or "")

        if status is not None:
            self._record_response(request_id, url, int(status))

        if status is None or int(status) < 400:
            return
        entry = NetworkFailure(
            url=url,
            method=self._request_methods.get(request_id, ""),
            status=int(status),
            status_text=str(_get(response, "statusText") or ""),
        )
        self._network_failures.add("network_failure", (url, int(status)), entry)

    def _on_loading_failed(self, params: Any) -> None:
        request_id = str(_get(params, "requestId") or "")
        url = str(_get(params, "documentURL") or self._request_urls.get(request_id, ""))
        error_text = str(_get(params, "errorText") or "loading failed")
        canceled = bool(_get(params, "canceled"))
        if canceled:
            return
        entry = NetworkFailure(
            url=url,
            method=self._request_methods.get(request_id, ""),
            error_text=error_text,
            failed=True,
            canceled=canceled,
        )
        self._network_failures.add("network_failure", (url, "failed", error_text), entry)


async def collect_dev_insights_during(
    session: Any,
    action: Any,
    *,
    url: str = "",
) -> DevInsights:
    """Run an async callable while capturing dev insights."""
    collector = DevInsightsCollector()
    await collector.start(session)
    try:
        await action()
    finally:
        from .verification import read_current_url

        await collector.snapshot_page_signals(session)
        final_url = url or await read_current_url(session)
        return collector.stop(url=final_url)


async def probe_nested_collectors(session: Any, base_url: str) -> dict[str, Any]:
    """Verify nested collectors both receive console errors (hub fan-out)."""
    from .verification import read_current_url

    outer = DevInsightsCollector()
    inner = DevInsightsCollector()
    await outer.start(session)
    await inner.start(session)
    b = base_url.rstrip("/")
    try:
        await session.navigate_to(f"{b}/edge-lab?devtest=1")
        await wait_until(
            lambda: any("EDGE_LAB_CONSOLE_ERROR" in e.text for e in outer._console_errors.values())
            and any("EDGE_LAB_CONSOLE_ERROR" in e.text for e in inner._console_errors.values()),
            timeout=5.0,
        )
        await outer.snapshot_page_signals(session)
        outer_insights = outer.stop(url=await read_current_url(session))
        inner_insights = inner.stop()
    except Exception as exc:
        outer.stop()
        inner.stop()
        return {"ok": False, "error": str(exc)}

    ok = bool(outer_insights.console_errors and inner_insights.console_errors)
    return {
        "ok": ok,
        "outer_errors": len(outer_insights.console_errors),
        "inner_errors": len(inner_insights.console_errors),
    }


async def probe_tier_a_dev_insights(session: Any, base_url: str) -> dict[str, Any]:
    """Exercise Tier A signals on /edge-lab?devtest=1 and verify capture."""
    from .scripted_actions import click_button_text
    from .verification import read_current_url

    collector = DevInsightsCollector()
    await collector.start(session)
    b = base_url.rstrip("/")
    try:
        await session.navigate_to(f"{b}/edge-lab?devtest=1")
        await wait_until(
            lambda: any("EDGE_LAB_CONSOLE_ERROR" in e.text for e in collector._console_errors.values()),
            timeout=5.0,
        )
        await click_button_text(session, "Trigger uncaught error")
        await wait_until(lambda: bool(collector._exceptions.values()), timeout=3.0)
        await collector.snapshot_page_signals(session)
        insights = collector.stop(url=await read_current_url(session))
    except Exception as exc:
        insights = collector.stop()
        return {"ok": False, "error": str(exc), "insights": insights.to_dict()}

    has_console = any("EDGE_LAB_CONSOLE_ERROR" in e.text for e in insights.console_errors)
    has_exception = any(
        "EDGE_LAB_UNCAUGHT" in e.text
        or "EDGE_LAB_UNCAUGHT" in e.stack
        or ("onClick" in e.stack and "EdgeLab.jsx" in (e.url or e.stack))
        for e in insights.exceptions
    )
    has_network = any(
        "dev-insights-missing" in n.url or (n.status is not None and n.status >= 404)
        for n in insights.network_failures
    )
    ok = has_console and has_exception and has_network
    return {
        "ok": ok,
        "has_console_error": has_console,
        "has_uncaught_exception": has_exception,
        "has_network_failure": has_network,
        "insights": insights.to_dict(),
    }


async def probe_tier_b_dev_insights(session: Any, base_url: str) -> dict[str, Any]:
    """Exercise Tier B signals on /edge-lab?devtestb=1 and verify capture."""
    from .scripted_actions import click_button_text
    from .verification import read_current_url

    collector = DevInsightsCollector()
    await collector.start(session)
    b = base_url.rstrip("/")
    try:
        await session.navigate_to(f"{b}/edge-lab?devtestb=1")
        await wait_until(
            lambda: any("dev-insights-slow" in s.url for s in collector._slow_requests.values()),
            timeout=8.0,
        )
        await click_button_text(session, "Show UI error banner")

        async def _ui_banner_visible() -> bool:
            from .verification import evaluate_js

            text = await evaluate_js(session, "document.body.innerText")
            return bool(text and "EDGE_LAB_UI_ERROR" in str(text))

        await wait_until_async(_ui_banner_visible, timeout=3.0)
        await collector.snapshot_page_signals(session)
        insights = collector.stop(url=await read_current_url(session))
    except Exception as exc:
        insights = collector.stop()
        return {"ok": False, "error": str(exc), "insights": insights.to_dict()}

    has_warn = any("EDGE_LAB_CONSOLE_WARN" in w.text for w in insights.console_warnings)
    has_api = any("dev-insights-ok" in c.url for c in insights.api_calls)
    has_slow = any("dev-insights-slow" in s.url for s in insights.slow_requests)
    has_ui = any("EDGE_LAB_UI_ERROR" in msg for msg in insights.ui_errors)
    has_meta = bool(insights.page_meta and insights.page_meta.title)
    ok = has_warn and has_api and has_slow and has_ui and has_meta
    return {
        "ok": ok,
        "has_console_warn": has_warn,
        "has_api_call": has_api,
        "has_slow_request": has_slow,
        "has_ui_error": has_ui,
        "has_page_meta": has_meta,
        "insights": insights.to_dict(),
    }
