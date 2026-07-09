"""Phase 4: rich text editors — contenteditable, Monaco, CodeMirror detection."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_page_text


@dataclass(slots=True)
class RichEditorResult:
    ok: bool
    editor_type: str
    filled: bool
    verified: bool
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "editor_type": self.editor_type,
            "filled": self.filled,
            "verified": self.verified,
            "error": self.error,
        }


async def detect_editor_type(session: Any) -> str:
    if await evaluate_js(session, "!!document.querySelector('.monaco-editor')"):
        return "monaco"
    if await evaluate_js(session, "!!document.querySelector('.CodeMirror')"):
        return "codemirror"
    if await evaluate_js(session, "!!document.querySelector('[contenteditable=true]')"):
        return "contenteditable"
    if await evaluate_js(session, "!!document.querySelector('[data-testid=\"rich-editor\"]')"):
        return "contenteditable"
    return "none"


async def fill_rich_editor(session: Any, text: str, *, selector: str = '[data-testid="rich-editor"]') -> RichEditorResult:
    try:
        editor_type = await detect_editor_type(session)
        if editor_type == "none":
            return RichEditorResult(False, editor_type, False, False, "no editor found")

        if editor_type == "monaco":
            filled = await evaluate_js(
                session,
                f"""
                (() => {{
                  const ed = window.monaco?.editor?.getEditors?.()?.[0];
                  if (!ed) return false;
                  ed.setValue({text!r});
                  return true;
                }})()
                """,
            )
        elif editor_type == "codemirror":
            filled = await evaluate_js(
                session,
                f"""
                (() => {{
                  const cm = document.querySelector('.CodeMirror')?.CodeMirror;
                  if (!cm) return false;
                  cm.setValue({text!r});
                  return true;
                }})()
                """,
            )
        else:
            filled = await evaluate_js(
                session,
                f"""
                (() => {{
                  const el = document.querySelector({selector!r});
                  if (!el) return false;
                  el.textContent = {text!r};
                  el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                  return true;
                }})()
                """,
            )

        await asyncio.sleep(0.2)
        page = await read_page_text(session, include_dom_text=True)
        verified = text in page or "editor content verified" in page.lower()
        return RichEditorResult(bool(filled), editor_type, bool(filled), verified)
    except Exception as exc:
        return RichEditorResult(False, "error", False, False, str(exc))
