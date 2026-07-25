"""Phase 1: independent verification — never trust agent self-report."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Last Runtime.evaluate exception message (cleared on each evaluate_js call).
_last_js_eval_error: str | None = None


def last_js_eval_error() -> str | None:
    return _last_js_eval_error


@dataclass(slots=True)
class SuccessCriteria:
    url_contains: list[str] = field(default_factory=list)
    url_not_contains: list[str] = field(default_factory=list)
    url_regex: str | None = None
    text_contains: list[str] = field(default_factory=list)
    text_absent: list[str] = field(default_factory=list)
    js_assertions: list[str] = field(default_factory=list)
    accept_urls: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VerificationResult:
    ok: bool
    url: str
    reasons: list[str] = field(default_factory=list)
    auto_merged: bool = False

    def feedback(self) -> str:
        if self.ok:
            return "verified" + (" (auto-merged)" if self.auto_merged else "")
        return "; ".join(self.reasons) or "verification failed"


async def read_page_text(browser_session: Any, *, include_dom_text: bool = False) -> str:
    parts: list[str] = []
    try:
        parts.append(await browser_session.get_state_as_text())
    except Exception:
        pass
    if include_dom_text:
        try:
            inner = await evaluate_js(browser_session, "document.body.innerText")
            if inner:
                parts.append(str(inner))
        except Exception:
            pass
    return "\n".join(parts)


async def read_current_url(browser_session: Any) -> str:
    try:
        return await browser_session.get_current_page_url()
    except Exception:
        return ""


async def evaluate_js(browser_session: Any, expression: str) -> Any:
    global _last_js_eval_error
    _last_js_eval_error = None
    expr = expression.strip()
    # Arrow / function expressions must be invoked — bare `() => ...` is truthy as a function object.
    if expr.startswith("() =>") or expr.startswith("()=>") or expr.startswith("function"):
        expr = f"({expr})()"
    elif not expr.startswith("(") and not expr.startswith("function"):
        expr = f"(() => {{ return ({expr}); }})()"

    try:
        cdp_session = await browser_session.get_or_create_cdp_session(target_id=None, focus=True)
        result = await cdp_session.cdp_client.send.Runtime.evaluate(
            params={"expression": expr, "returnByValue": True},
            session_id=cdp_session.session_id,
        )
        if result and result.get("exceptionDetails"):
            details = result["exceptionDetails"]
            exc = details.get("exception") if isinstance(details, dict) else None
            msg = ""
            if isinstance(exc, dict):
                msg = str(exc.get("description") or exc.get("value") or "")
            if not msg and isinstance(details, dict):
                msg = str(details.get("text") or details.get("description") or "js exception")
            _last_js_eval_error = (msg or "js exception")[:240]
            return None
        if result and "result" in result and "value" in result["result"]:
            return result["result"]["value"]
    except Exception as exc:
        _last_js_eval_error = str(exc)[:240]
    return None


async def _check_primary(browser_session: Any, criteria: SuccessCriteria, url: str) -> list[str]:
    reasons: list[str] = []

    for needle in criteria.url_contains:
        if needle.lower() not in url.lower():
            reasons.append(f"url missing '{needle}' (current: {url})")

    for needle in criteria.url_not_contains:
        if needle.lower() in url.lower():
            reasons.append(f"url must not contain '{needle}'")

    if criteria.url_regex and not re.search(criteria.url_regex, url):
        reasons.append(f"url does not match /{criteria.url_regex}/")

    needs_text = bool(criteria.text_contains or criteria.text_absent)
    page_text = await read_page_text(browser_session, include_dom_text=needs_text) if needs_text else ""
    haystack = page_text.lower()

    for needle in criteria.text_contains:
        if needle.lower() not in haystack:
            reasons.append(f"expected text '{needle}' not found on page")

    for needle in criteria.text_absent:
        if needle.lower() in haystack:
            reasons.append(f"unexpected text '{needle}' still present")

    for js_expr in criteria.js_assertions:
        value = await evaluate_js(browser_session, js_expr)
        err = last_js_eval_error()
        label = _js_assertion_label(js_expr)
        if err:
            reasons.append(f"{label}: js error: {err}" if label else f"js assertion error: {err}")
        elif not value:
            if label:
                reasons.append(f"{label}: failed")
            else:
                reasons.append(f"js assertion failed: {js_expr[:60]}")

    return reasons


def _js_assertion_label(js_expr: str) -> str | None:
    """Map known convention assertions to stable signal names for hosts."""
    try:
        from navigation.coordination_intelligence.planning.chrome_conventions import (
            CHROME_PERMANENCE_ASSERTION,
            HORIZONTAL_OVERFLOW_ASSERTION,
        )
    except Exception:
        return None
    if js_expr == CHROME_PERMANENCE_ASSERTION or (
        "hasStickyChain" in js_expr and "querySelectorAll" in js_expr and "aside" in js_expr
    ):
        return "chrome_permanence_failed"
    if js_expr == HORIZONTAL_OVERFLOW_ASSERTION or (
        "scrollWidth" in js_expr and "innerWidth" in js_expr
    ):
        return "horizontal_overflow_failed"
    if "getBoundingClientRect" in js_expr and "section" in js_expr.lower():
        return "section_presence_failed"
    return None


async def verify(browser_session: Any, criteria: SuccessCriteria) -> VerificationResult:
    url = await read_current_url(browser_session)
    reasons = await _check_primary(browser_session, criteria, url)
    if not reasons:
        return VerificationResult(ok=True, url=url)

    for accept in criteria.accept_urls:
        if accept.lower() in url.lower():
            return VerificationResult(ok=True, url=url, auto_merged=True)

    return VerificationResult(ok=False, url=url, reasons=reasons)
