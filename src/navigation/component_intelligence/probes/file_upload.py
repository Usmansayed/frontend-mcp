"""Phase 4: programmatic file upload via CDP."""
from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_page_text


@dataclass(slots=True)
class FileUploadResult:
    ok: bool
    filename: str
    displayed: bool
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "filename": self.filename,
            "displayed": self.displayed,
            "error": self.error,
        }


async def upload_test_file(
    session: Any,
    *,
    input_selector: str = '[data-testid="file-input"]',
    content: str = "edge-lab upload test",
    suffix: str = ".txt",
) -> FileUploadResult:
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as f:
            f.write(content)
            tmp_path = Path(f.name)

        filename = tmp_path.name
        cdp = await session.get_or_create_cdp_session(target_id=None, focus=True)
        doc = await cdp.cdp_client.send.DOM.getDocument(session_id=cdp.session_id)
        root_id = doc["root"]["nodeId"]
        sel = await cdp.cdp_client.send.DOM.querySelector(
            params={"nodeId": root_id, "selector": input_selector},
            session_id=cdp.session_id,
        )
        node_id = sel.get("nodeId")
        if not node_id:
            return FileUploadResult(False, filename, False, "file input not found")

        await cdp.cdp_client.send.DOM.setFileInputFiles(
            params={"files": [str(tmp_path.resolve())], "nodeId": node_id},
            session_id=cdp.session_id,
        )

        await evaluate_js(
            session,
            f"""
            (() => {{
              const input = document.querySelector({input_selector!r});
              if (!input) return false;
              input.dispatchEvent(new Event('change', {{ bubbles: true }}));
              input.dispatchEvent(new Event('input', {{ bubbles: true }}));
              return true;
            }})()
            """,
        )
        await asyncio.sleep(0.3)

        page = await read_page_text(session, include_dom_text=True)
        base_name = Path(filename).name
        displayed = base_name in page or "uploaded:" in page.lower()
        return FileUploadResult(displayed, base_name, displayed)
    except Exception as exc:
        return FileUploadResult(False, tmp_path.name if tmp_path else "", False, str(exc))
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
