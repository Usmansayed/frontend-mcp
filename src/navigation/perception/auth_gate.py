"""Phase 1: stop on human-auth surfaces — never loop on login/MFA/CAPTCHA."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .verification import read_current_url, read_page_text

LOGIN_URL_PATTERNS = ("/login", "/signin", "/sign-in", "/auth")
HUMAN_AUTH_TEXT = (
    "captcha",
    "two-factor",
    "2fa",
    "verification code",
    "authenticator",
    "mfa",
    "one-time password",
    "otp",
)
PASSWORD_FIELD_JS = "document.querySelector('input[type=password]') !== null"


@dataclass(slots=True)
class AuthGateResult:
    requires_human: bool
    reason: str
    url: str

    def to_dict(self) -> dict:
        return {
            "requires_human": self.requires_human,
            "reason": self.reason,
            "url": self.url,
        }


async def check_auth_gate(session: Any) -> AuthGateResult:
    url = await read_current_url(session)
    url_lower = url.lower()
    text = (await read_page_text(session, include_dom_text=True)).lower()

    for pattern in LOGIN_URL_PATTERNS:
        if pattern in url_lower:
            return AuthGateResult(True, f"login route detected ({pattern})", url)

    for marker in HUMAN_AUTH_TEXT:
        if marker in text:
            return AuthGateResult(True, f"human-auth marker: {marker}", url)

    if re.search(r"\bsign\s*in\b", text) and "password" in text:
        from .verification import evaluate_js

        if await evaluate_js(session, PASSWORD_FIELD_JS):
            return AuthGateResult(True, "sign-in form with password field", url)

    return AuthGateResult(False, "no human-auth gate", url)
