"""Unit tests for visual_browser_intelligence.verify — no real browser (T0)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.visual_browser_intelligence.verify.verification import (
    SuccessCriteria,
    VerificationResult,
    verify,
)


class _FakeSession:
    """Minimal browser session stub. Enough surface for `verify` without CDP."""

    def __init__(self, *, url: str = "", page_text: str = "", inner_text: str = "", js_returns: dict[str, object] | None = None) -> None:
        self._url = url
        self._page_text = page_text
        self._inner_text = inner_text
        self._js = js_returns or {}

    async def get_current_page_url(self) -> str:
        return self._url

    async def get_state_as_text(self) -> str:
        return self._page_text

    async def get_or_create_cdp_session(self, *, target_id=None, focus=True):
        return _FakeCdpSession(self._inner_text, self._js)


class _FakeCdpSession:
    def __init__(self, inner_text: str, js: dict[str, object]) -> None:
        self.session_id = "fake-session"
        self.cdp_client = _FakeCdpClient(inner_text, js)


class _FakeCdpClient:
    def __init__(self, inner_text: str, js: dict[str, object]) -> None:
        self.send = _FakeRuntimeNamespace(inner_text, js)


class _FakeRuntimeNamespace:
    def __init__(self, inner_text: str, js: dict[str, object]) -> None:
        self.Runtime = _FakeRuntime(inner_text, js)


class _FakeRuntime:
    def __init__(self, inner_text: str, js: dict[str, object]) -> None:
        self._inner_text = inner_text
        self._js = js

    async def evaluate(self, params: dict, session_id: str) -> dict:
        expr = params.get("expression", "")
        if "document.body.innerText" in expr:
            return {"result": {"value": self._inner_text}}
        for key, value in self._js.items():
            if key in expr:
                return {"result": {"value": value}}
        return {"result": {"value": None}}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_url_contains_positive() -> None:
    session = _FakeSession(url="https://example.com/dashboard")
    result = await verify(session, SuccessCriteria(url_contains=["/dashboard"]))
    assert isinstance(result, VerificationResult)
    assert result.ok is True
    assert result.url == "https://example.com/dashboard"
    assert result.reasons == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_url_contains_negative_gives_reason() -> None:
    session = _FakeSession(url="https://example.com/login")
    result = await verify(session, SuccessCriteria(url_contains=["/dashboard"]))
    assert result.ok is False
    assert any("/dashboard" in reason for reason in result.reasons)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_url_not_contains_negative() -> None:
    session = _FakeSession(url="https://example.com/error?code=500")
    result = await verify(session, SuccessCriteria(url_not_contains=["error"]))
    assert result.ok is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_url_regex() -> None:
    session = _FakeSession(url="https://example.com/users/42/edit")
    ok = await verify(session, SuccessCriteria(url_regex=r"/users/\d+/edit"))
    fail = await verify(session, SuccessCriteria(url_regex=r"/admin"))
    assert ok.ok is True
    assert fail.ok is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_text_contains_uses_inner_text() -> None:
    session = _FakeSession(
        url="https://example.com/",
        page_text="Header nav",
        inner_text="Welcome back, Usman",
    )
    result = await verify(session, SuccessCriteria(text_contains=["welcome back"]))
    assert result.ok is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_text_absent_negative() -> None:
    session = _FakeSession(
        url="https://example.com/",
        page_text="Error: something broke",
        inner_text="Error: something broke",
    )
    result = await verify(session, SuccessCriteria(text_absent=["error"]))
    assert result.ok is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_js_assertion_pass_and_fail() -> None:
    passing = _FakeSession(url="https://example.com/", js_returns={"isReady": True})
    failing = _FakeSession(url="https://example.com/", js_returns={"isReady": False})
    ok = await verify(passing, SuccessCriteria(js_assertions=["window.isReady"]))
    fail = await verify(failing, SuccessCriteria(js_assertions=["window.isReady"]))
    assert ok.ok is True
    assert fail.ok is False
    assert any("js assertion failed" in r for r in fail.reasons)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_accept_urls_auto_merges_failure() -> None:
    """When primary criteria fail but URL matches an accept_url, verification auto-merges."""
    session = _FakeSession(url="https://example.com/checkout/success")
    criteria = SuccessCriteria(
        url_contains=["/dashboard"],
        accept_urls=["/checkout/success"],
    )
    result = await verify(session, criteria)
    assert result.ok is True
    assert result.auto_merged is True


@pytest.mark.unit
def test_verification_result_feedback_ok_vs_fail() -> None:
    ok = VerificationResult(ok=True, url="https://x/")
    assert ok.feedback() == "verified"

    merged = VerificationResult(ok=True, url="https://x/", auto_merged=True)
    assert "auto-merged" in merged.feedback()

    fail = VerificationResult(ok=False, url="https://x/", reasons=["missing text 'foo'"])
    assert "missing text 'foo'" in fail.feedback()

    empty_fail = VerificationResult(ok=False, url="https://x/")
    assert empty_fail.feedback() == "verification failed"
