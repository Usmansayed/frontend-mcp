"""Phase 4: observe DOM changes without URL navigation (WebSocket / live UI)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .verification import evaluate_js, read_current_url


@dataclass(slots=True)
class LiveDomResult:
    ok: bool
    url_unchanged: bool
    counter_increased: bool
    start_value: int
    end_value: int
    samples: int
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "url_unchanged": self.url_unchanged,
            "counter_increased": self.counter_increased,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "samples": self.samples,
            "error": self.error,
        }


async def _read_counter(session: Any, selector: str = '[data-testid="live-counter"]') -> int:
    raw = await evaluate_js(
        session,
        f"""
        (() => {{
          const el = document.querySelector({selector!r});
          if (!el) return -1;
          const m = el.textContent.match(/(\\d+)/);
          return m ? parseInt(m[1], 10) : -1;
        }})()
        """,
    )
    return int(raw) if raw is not None and raw >= 0 else -1


async def observe_live_dom(
    session: Any,
    *,
    wait_seconds: float = 1.2,
    samples: int = 3,
) -> LiveDomResult:
    try:
        start_url = await read_current_url(session)
        start = await _read_counter(session)
        if start < 0:
            return LiveDomResult(False, True, False, 0, 0, 0, "live counter not found")

        end = start
        for _ in range(samples):
            await asyncio.sleep(wait_seconds / samples)
            end = await _read_counter(session)

        final_url = await read_current_url(session)
        url_unchanged = start_url == final_url
        counter_increased = end > start
        ok = url_unchanged and counter_increased

        return LiveDomResult(
            ok=ok,
            url_unchanged=url_unchanged,
            counter_increased=counter_increased,
            start_value=start,
            end_value=end,
            samples=samples,
        )
    except Exception as exc:
        return LiveDomResult(False, False, False, 0, 0, 0, str(exc))
