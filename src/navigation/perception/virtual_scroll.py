"""Phase 4: scroll virtualized lists until DOM stabilizes."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .verification import evaluate_js


@dataclass(slots=True)
class VirtualScrollResult:
    ok: bool
    rows_seen: int
    target_found: bool
    scroll_steps: int
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "rows_seen": self.rows_seen,
            "target_found": self.target_found,
            "scroll_steps": self.scroll_steps,
            "error": self.error,
        }


async def scroll_until_item_found(
    session: Any,
    *,
    list_selector: str = '[data-testid="virtual-list"]',
    target_row_id: int = 150,
    max_steps: int = 30,
) -> VirtualScrollResult:
    try:
        rows_seen: set[int] = set()
        target_found = False
        steps = 0

        for step in range(max_steps):
            steps = step + 1
            ids = await evaluate_js(
                session,
                f"""
                Array.from(document.querySelectorAll({list_selector!r} + ' [data-row-id]'))
                  .map(el => parseInt(el.getAttribute('data-row-id'), 10))
                  .filter(n => !isNaN(n))
                """,
            )
            if isinstance(ids, list):
                for i in ids:
                    rows_seen.add(int(i))
                    if int(i) == target_row_id:
                        target_found = True

            if target_found:
                break

            at_end = await evaluate_js(
                session,
                f"""
                (() => {{
                  const el = document.querySelector({list_selector!r});
                  if (!el) return true;
                  const prev = el.scrollTop;
                  el.scrollTop += 180;
                  return el.scrollTop === prev;
                }})()
                """,
            )
            if at_end:
                break
            await asyncio.sleep(0.15)

        ok = target_found and len(rows_seen) > 15
        return VirtualScrollResult(
            ok=ok,
            rows_seen=len(rows_seen),
            target_found=target_found,
            scroll_steps=steps,
        )
    except Exception as exc:
        return VirtualScrollResult(ok=False, rows_seen=0, target_found=False, scroll_steps=0, error=str(exc))
