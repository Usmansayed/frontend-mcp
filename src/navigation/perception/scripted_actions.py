"""CDP helpers for deterministic browser actions."""
from __future__ import annotations

from typing import Any

from .verification import evaluate_js


async def click_button_text(session: Any, text: str) -> bool:
    return bool(
        await evaluate_js(
            session,
            f"""
            (() => {{
              const btn = Array.from(document.querySelectorAll('button'))
                .find(b => b.textContent.includes({text!r}));
              if (!btn) return false;
              btn.click();
              return true;
            }})()
            """,
        )
    )


async def click_link_text(session: Any, text: str) -> bool:
    return bool(
        await evaluate_js(
            session,
            f"""
            (() => {{
              const link = Array.from(document.querySelectorAll('a'))
                .find(a => a.textContent.includes({text!r}));
              if (!link) return false;
              link.click();
              return true;
            }})()
            """,
        )
    )


async def set_input_by_label(session: Any, label_text: str, value: str) -> bool:
    return bool(
        await evaluate_js(
            session,
            f"""
            (() => {{
              const labels = Array.from(document.querySelectorAll('label'));
              const label = labels.find(l => l.textContent.trim().startsWith({label_text!r}));
              if (!label) return false;
              const field = label.closest('.field') || label.parentElement;
              const input = field?.querySelector('input, select, textarea');
              if (!input) return false;
              const setter = Object.getOwnPropertyDescriptor(
                input.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype,
                'value'
              )?.set;
              if (!setter) return false;
              setter.call(input, {value!r});
              input.dispatchEvent(new Event('input', {{ bubbles: true }}));
              input.dispatchEvent(new Event('change', {{ bubbles: true }}));
              return true;
            }})()
            """,
        )
    )
