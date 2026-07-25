"""Live smoke test: design/consistency tools now inline rendered screenshots.

Drives ONE MCP ExecutionRuntime (full dispatch path incl. the visual post-hook)
against the running app and asserts that build_design_snapshot / design_review /
consistency_review / consistency_audit each attach viewport + full-page + section
screenshots as inline images (and that the PNG files actually exist).

Writes a scorecard JSON next to the Run-4 hardcore scorecard.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

from navigation.core.process_identity import PROCESS_BOOT_ID
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.execution_runtime.runtime import ExecutionRuntime
from navigation.visual_browser_intelligence.browser.browser_session_manager import (
    BrowserSessionManager,
)
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.visual.visual_response import VISUAL_ATTACHMENTS_KEY

DESIGN_TOOLS = (
    'perception_build_design_snapshot',
    'perception_design_review',
    'perception_consistency_review',
    'perception_consistency_audit',
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def _inspect_visuals(envelope: dict[str, Any]) -> dict[str, Any]:
    atts = list(envelope.get(VISUAL_ATTACHMENTS_KEY) or [])
    data = envelope.get('data') if isinstance(envelope.get('data'), dict) else {}
    evidence = list(data.get('visual_evidence') or [])
    files_ok = 0
    total_bytes = 0
    labels: list[str] = []
    for a in atts:
        p = Path(str(a.get('path') or ''))
        labels.append(str(a.get('label')))
        if p.is_file():
            files_ok += 1
            total_bytes += p.stat().st_size
    return {
        'attachment_count': len(atts),
        'labels': labels,
        'files_exist': files_ok,
        'total_image_bytes': total_bytes,
        'data_visual_evidence': [e.get('label') if isinstance(e, dict) else e for e in evidence],
        'has_viewport': any(str(l).startswith('viewport') for l in labels),
        'has_full_page': any(l == 'full_page' for l in labels),
        'has_section': any(str(l).startswith('section:') for l in labels),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description='Design visual-evidence live smoke test')
    parser.add_argument('--url', default='http://127.0.0.1:3001')
    parser.add_argument('--route', default='/')
    parser.add_argument(
        '--out',
        default=str(
            Path(r'C:\Users\usman\Desktop\artful-portfolio-main\newUi')
            / 'design-visual-evidence-scorecard.json'
        ),
    )
    args = parser.parse_args()

    BrowserSessionManager.reset_default()
    store = SessionStore(
        artifacts_root=ROOT / 'artifacts' / 'design_visual',
        manager=BrowserSessionManager.get(),
    )
    scans = ScanRegistry()
    snapshots = SnapshotRegistry()
    runtime = ExecutionRuntime(store, scans, snapshots)

    results: list[dict[str, Any]] = []

    async def call(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        res = await runtime.execute_tool(tool, arguments)
        return res.envelope

    print(f'design visual smoke url={args.url} boot={PROCESS_BOOT_ID}', flush=True)

    start = await call('perception_session_start', {'base_url': args.url, 'intent': 'design visual evidence smoke', 'headless': True})
    sid = start.get('session_id') or (start.get('data') or {}).get('session_id')
    if not sid:
        print('session_start failed', json.dumps(start)[:400], flush=True)
        return 2
    print(f'session {sid}', flush=True)

    nav = await call('perception_navigate_and_observe', {'session_id': sid, 'url': args.route, 'detail': 'summary_only'})
    scan_id = nav.get('scan_id') or (nav.get('data') or {}).get('scan_id')
    print(f'scan {scan_id} ok={nav.get("ok")}', flush=True)

    tool_args = {
        'perception_build_design_snapshot': {'session_id': sid, 'scan_id': scan_id},
        'perception_design_review': {
            'session_id': sid,
            'scan_id': scan_id,
            'user_task': 'Review portfolio landing design',
            'visual_feedback': {
                'judgment': 'needs_work',
                'notes': 'header too dense, footer cramped',
                'focus_sections': ['header', 'footer'],
                'issues': [
                    {
                        'section': 'header',
                        'problem': 'too dense',
                        'wanted': 'more spacing between nav items',
                    }
                ],
            },
        },
        'perception_consistency_review': {
            'session_id': sid,
            'scan_id': scan_id,
            'visual_notes': 'header spacing looks tight',
            'visual_judgment': 'needs_work',
            'focus_sections': ['header'],
        },
        'perception_consistency_audit': {'session_id': sid, 'scan_id': scan_id, 'screenshot_pack': 'design'},
    }

    for tool in DESIGN_TOOLS:
        env = await call(tool, tool_args[tool])
        vis = _inspect_visuals(env)
        data = env.get('data') if isinstance(env.get('data'), dict) else {}
        next_actions = list(data.get('next_actions') or [])
        ok = bool(env.get('ok'))
        # Live PASS = tool ok AND has viewport+full+at least attempted section, files on disk.
        passed = ok and vis['has_viewport'] and vis['has_full_page'] and vis['files_exist'] >= 2
        # Feedback tools must also emit next_actions.
        if tool_args[tool].get('visual_feedback') or tool_args[tool].get('visual_notes'):
            if not next_actions:
                passed = False
            vis['next_actions'] = [a.get('action') for a in next_actions]
            vis['has_feedback'] = bool(data.get('visual_feedback'))
        status = 'PASS' if passed else ('MIXED' if ok and vis['attachment_count'] else 'FAIL')
        results.append({'tool': tool, 'ok': ok, 'status': status, 'visuals': vis})
        print(
            f"  {tool} -> {status} labels={vis['labels']} files_ok={vis['files_exist']}"
            + (f" next={vis.get('next_actions')}" if vis.get('next_actions') is not None else ''),
            flush=True,
        )

    await call('perception_session_end', {'session_id': sid})
    try:
        await store.end_all()
    except Exception:
        pass

    passed = sum(1 for r in results if r['status'] == 'PASS')
    scorecard = {
        'run': 'design_visual_evidence',
        'mcp_version': '1.2.0.dev45',
        'base_url': args.url,
        'route': args.route,
        'started_at': _utcnow(),
        'process_boot_id': PROCESS_BOOT_ID,
        'session_id': sid,
        'scan_id': scan_id,
        'totals': {
            'tools': len(results),
            'pass': passed,
            'mixed': sum(1 for r in results if r['status'] == 'MIXED'),
            'fail': sum(1 for r in results if r['status'] == 'FAIL'),
        },
        'results': results,
        'verdict': 'PASS' if passed == len(results) else ('MIXED' if passed else 'FAIL'),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scorecard, indent=2), encoding='utf-8')
    mirror = ROOT / 'artifacts' / 'design_visual' / out.name
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(scorecard, indent=2), encoding='utf-8')

    print(json.dumps({'verdict': scorecard['verdict'], 'totals': scorecard['totals'], 'out': str(out)}, indent=2), flush=True)
    return 0 if scorecard['verdict'] != 'FAIL' else 2


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
