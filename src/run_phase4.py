"""Phase 4: edge-case probes (exploration, flags, iframe, scroll, editors, upload, live DOM)."""
from __future__ import annotations

import argparse
import asyncio
import sys

import _bootstrap  # noqa: F401
from _bootstrap import ROOT, SANDBOX_ROOT

from dotenv import load_dotenv

from navigation.codeGraph import create_code_graph
from navigation.perception import SuccessCriteria, artifact_dir, dump_json
from navigation.perception.exploration import explore_with_hints
from navigation.perception.feature_flags import probe_feature_flag
from navigation.perception.file_upload import upload_test_file
from navigation.perception.iframe_context import probe_iframe_interaction
from navigation.perception.rich_editors import fill_rich_editor
from navigation.perception.virtual_scroll import scroll_until_item_found
from navigation.perception.websocket_observer import observe_live_dom

load_dotenv(ROOT / ".env")
load_dotenv()

EDGE_LAB = "/edge-lab"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4: edge-case perception probes")
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    from browser_use import BrowserProfile, BrowserSession

    out = artifact_dir("phase4", ROOT / "artifacts" / "phase4")
    report: dict = {"phase": 4, "ok": False, "tests": {}}

    code_graph = create_code_graph(SANDBOX_ROOT, enabled=True)
    session = BrowserSession(browser_profile=BrowserProfile(headless=args.headless))

    try:
        await session.start()
        base = args.url.rstrip("/")
        await session.navigate_to(f"{base}{EDGE_LAB}")
        await asyncio.sleep(0.4)

        # 1. Feature flags
        flags = await probe_feature_flag(
            session, args.url, EDGE_LAB,
            flag_query="beta=1",
            feature_text="Beta feature enabled",
        )
        report["tests"]["feature_flags"] = flags.to_dict()

        await session.navigate_to(f"{base}{EDGE_LAB}")
        await asyncio.sleep(0.3)

        # 2. iframe
        iframe = await probe_iframe_interaction(session)
        report["tests"]["iframe"] = iframe.to_dict()

        # 3. Virtual scroll
        scroll = await scroll_until_item_found(session, target_row_id=150)
        report["tests"]["virtual_scroll"] = scroll.to_dict()

        # 4. Rich editor
        editor = await fill_rich_editor(session, "edge-ok")
        report["tests"]["rich_editor"] = editor.to_dict()

        # 5. File upload
        upload = await upload_test_file(session)
        report["tests"]["file_upload"] = upload.to_dict()

        # 6. Live DOM (no URL change)
        live = await observe_live_dom(session)
        report["tests"]["live_dom"] = live.to_dict()

        # 7. CRG-guided exploration
        explore = await explore_with_hints(
            session,
            code_graph,
            "find edge lab page",
            base_url=args.url,
            success=SuccessCriteria(url_contains=["/edge-lab"], text_contains=["Edge case lab"]),
            candidate_paths=["/edge-lab"],
        )
        report["tests"]["exploration"] = explore.to_dict()

        report["ok"] = all(
            report["tests"][k].get("ok", False)
            for k in (
                "feature_flags",
                "iframe",
                "virtual_scroll",
                "rich_editor",
                "file_upload",
                "live_dom",
                "exploration",
            )
        )
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        try:
            await session.kill()
        except Exception:
            pass

    dump_json(out / "report.json", report)
    dump_json(ROOT / "artifacts" / "phase4" / "report.json", report)

    print(f"Phase 4: {'PASS' if report['ok'] else 'FAIL'}")
    for name, result in report.get("tests", {}).items():
        status = "ok" if result.get("ok") else "FAIL"
        print(f"  [{status}] {name}")
    print(f"  artifacts: {out}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    if not SANDBOX_ROOT.exists():
        print("sandbox/ missing")
        sys.exit(1)
    raise SystemExit(asyncio.run(main()))
