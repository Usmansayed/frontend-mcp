"""Phase 4: iframe-aware interaction (same-origin / srcdoc frames)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_page_text


@dataclass(slots=True)
class IframeProbeResult:
    ok: bool
    frame_count: int
    clicked_in_frame: bool
    frame_text: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "frame_count": self.frame_count,
            "clicked_in_frame": self.clicked_in_frame,
            "frame_text": self.frame_text[:500],
            "error": self.error,
        }


async def probe_iframe_interaction(
    session: Any,
    *,
    iframe_selector: str = '[data-testid="edge-iframe"]',
    button_id: str = "frame-btn",
    expected_text: str = "clicked",
) -> IframeProbeResult:
    try:
        frame_count = await evaluate_js(
            session,
            "document.querySelectorAll('iframe').length",
        )
        frame_count = int(frame_count or 0)

        clicked = await evaluate_js(
            session,
            f"""
            (() => {{
              const frame = document.querySelector({iframe_selector!r});
              if (!frame || !frame.contentDocument) return false;
              const btn = frame.contentDocument.getElementById({button_id!r});
              if (!btn) return false;
              btn.click();
              const out = frame.contentDocument.getElementById('out');
              return out && out.textContent === {expected_text!r};
            }})()
            """,
        )

        frame_text = await evaluate_js(
            session,
            f"""
            (() => {{
              const frame = document.querySelector({iframe_selector!r});
              return frame?.contentDocument?.body?.innerText || '';
            }})()
            """,
        )

        ok = bool(clicked) and frame_count >= 1
        return IframeProbeResult(
            ok=ok,
            frame_count=frame_count,
            clicked_in_frame=bool(clicked),
            frame_text=str(frame_text or ""),
        )
    except Exception as exc:
        return IframeProbeResult(ok=False, frame_count=0, clicked_in_frame=False, error=str(exc))
