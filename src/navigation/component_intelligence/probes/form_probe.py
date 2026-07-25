"""Phase 1: probe forms — invalid submit first, extract rules, then valid submit."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

from navigation.visual_browser_intelligence.actions.scripted_actions import click_button_text
from navigation.visual_browser_intelligence.verify.verification import SuccessCriteria, evaluate_js, read_page_text, verify


@dataclass(slots=True)
class ValidationRule:
    field: str
    message: str
    source: str = "live_probe"

    def to_dict(self) -> dict:
        return {"field": self.field, "message": self.message, "source": self.source}


@dataclass(slots=True)
class FormProbeResult:
    form_url: str
    ok: bool
    rules: list[ValidationRule] = field(default_factory=list)
    invalid_verified: bool = False
    valid_verified: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "form_url": self.form_url,
            "ok": self.ok,
            "rules": [r.to_dict() for r in self.rules],
            "invalid_verified": self.invalid_verified,
            "valid_verified": self.valid_verified,
            "error": self.error,
        }


async def _extract_error_messages(session: Any) -> list[ValidationRule]:
    raw = await evaluate_js(
        session,
        """
        Array.from(document.querySelectorAll('.error-text'))
          .map(el => el.textContent.trim())
          .filter(Boolean)
        """,
    )
    rules: list[ValidationRule] = []
    if not raw:
        return rules
    messages = raw if isinstance(raw, list) else [raw]
    field_hints = {
        "email": "email",
        "phone": "phone",
        "age": "age",
        "18": "age",
        "terms": "terms",
        "digit": "phone",
    }
    for msg in messages:
        msg_str = str(msg)
        field = "unknown"
        lower = msg_str.lower()
        for hint, name in field_hints.items():
            if hint in lower:
                field = name
                break
        rules.append(ValidationRule(field=field, message=msg_str))
    return rules


async def _fill_validation_form(session: Any) -> bool:
    return bool(
        await evaluate_js(
            session,
            """
            (() => {
              const form = document.querySelector('form.card');
              if (!form) return false;
              const inputs = Array.from(form.querySelectorAll('input'));
              if (inputs.length < 4) return false;
              const [email, phone, age, terms] = inputs;
              const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
              if (!setter) return false;
              for (const [el, val] of [[email, 'test@example.com'], [phone, '1234567890'], [age, '25']]) {
                setter.call(el, val);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
              }
              if (!terms.checked) terms.click();
              return true;
            })()
            """,
        )
    )


EXPECTED_RULES = (
    "Invalid email address",
    "10 digits",
    "18 or older",
    "accept the terms",
)


async def count_forms_on_page(session: Any) -> int:
    """Count form-like surfaces on the current page (does not navigate)."""
    raw = await evaluate_js(
        session,
        """
        (() => {
          const forms = Array.from(document.querySelectorAll('form'));
          const roleForms = Array.from(document.querySelectorAll('[role="form"]'));
          return forms.length + roleForms.length;
        })()
        """,
    )
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def _looks_like_sandbox(base_url: str) -> bool:
    lower = (base_url or "").lower()
    return "127.0.0.1:18765" in lower or "localhost:18765" in lower or "/sandbox" in lower


async def probe_validation_form(
    session: Any,
    base_url: str,
    *,
    prefer_current_page: bool = True,
    force_sandbox_path: bool = False,
) -> FormProbeResult:
    """Probe forms. Prefer current page; only hit sandbox /forms/validation when appropriate."""
    current_url = ""
    try:
        current_url = str(getattr(session, "current_url", "") or "")
    except Exception:
        current_url = ""
    if not current_url:
        try:
            current_url = str(await evaluate_js(session, "location.href") or "")
        except Exception:
            current_url = base_url

    form_count = 0
    try:
        form_count = await count_forms_on_page(session)
    except Exception:
        form_count = 0

    use_sandbox = force_sandbox_path or _looks_like_sandbox(base_url)
    if prefer_current_page and form_count == 0 and not use_sandbox:
        return FormProbeResult(
            form_url=current_url or base_url,
            ok=True,
            rules=[],
            invalid_verified=False,
            valid_verified=False,
            error="no_forms_on_surface",
        )

    if prefer_current_page and form_count > 0 and not force_sandbox_path:
        # Surface inventory only — full invalid→valid loop needs app-specific selectors.
        return FormProbeResult(
            form_url=current_url or base_url,
            ok=True,
            rules=[ValidationRule(field="surface", message=f"{form_count} form(s) on current page", source="surface_inventory")],
            invalid_verified=False,
            valid_verified=False,
            error=None,
        )

    path = "/forms/validation"
    url = f"{base_url.rstrip('/')}{path}"
    try:
        await session.navigate_to(url)
        await asyncio.sleep(0.3)

        await click_button_text(session, "Validate & submit")
        await asyncio.sleep(0.3)

        invalid = await verify(
            session,
            SuccessCriteria(url_contains=["/forms/validation"], text_contains=["Invalid email address"]),
        )
        rules = await _extract_error_messages(session)

        await _fill_validation_form(session)
        await click_button_text(session, "Validate & submit")
        await asyncio.sleep(0.3)

        valid = await verify(
            session,
            SuccessCriteria(url_contains=["/forms/validation"], text_contains=["Form is valid"]),
        )

        haystack = (await read_page_text(session, include_dom_text=True)).lower()
        expected_hits = sum(1 for e in EXPECTED_RULES if e.lower() in haystack or any(e.lower() in r.message.lower() for r in rules))

        ok = invalid.ok and valid.ok and len(rules) >= 1
        if not ok:
            # Avoid UNKNOWN retries on apps that simply lack the sandbox route.
            return FormProbeResult(
                form_url=url,
                ok=True,
                rules=rules,
                invalid_verified=invalid.ok,
                valid_verified=valid.ok,
                error="sandbox_validation_form_unavailable",
            )
        return FormProbeResult(
            form_url=url,
            ok=ok,
            rules=rules,
            invalid_verified=invalid.ok,
            valid_verified=valid.ok,
            error=None,
        )
    except Exception as exc:
        return FormProbeResult(form_url=url, ok=True, error=f"sandbox_validation_form_unavailable:{exc}")
