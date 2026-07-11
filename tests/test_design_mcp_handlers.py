"""MCP design pipeline handler tests (no browser)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRegistry
from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.mcp.design_intelligence_handlers import (
	handle_build_design_snapshot,
	handle_consistency_review,
	handle_design_review,
)
from navigation.visual_browser_intelligence.browser.session_store import SessionStore

FIXTURE = {
	'url': 'http://localhost:5173/login',
	'elements': [
		{
			'tag': 'button',
			'selector': 'button',
			'text': 'Continue',
			'classes': ['primary'],
			'style': {
				'fontSize': '13px',
				'color': '#ff0000',
				'backgroundColor': '#00ff00',
				'padding': '11px',
				'borderRadius': '5px',
			},
		},
	],
	'visual_insights': {
		'issues': [{'kind': 'horizontal_overflow', 'severity': 'blocking', 'detail': 'scrollWidth=2000'}],
		'blocking': ['horizontal_overflow'],
	},
}


async def test_design_review_from_snapshot_id() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	snapshots = SnapshotRegistry()
	rec = snapshots.register(snapshot=snapshot.to_dict(), url=snapshot.url)

	result = await handle_design_review(
		SessionStore(),
		ScanRegistry(),
		snapshots,
		{'snapshot_id': rec.snapshot_id, 'user_task': 'Sign in'},
	)
	assert result['ok'] is True
	data = result['data']
	assert data['finding_count'] >= 1
	assert 'summary' in data
	assert data.get('consensus_removed_duplicates', 0) >= 0


async def test_consistency_review_from_snapshot_id() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	snapshots = SnapshotRegistry()
	rec = snapshots.register(snapshot=snapshot.to_dict(), url=snapshot.url)

	result = await handle_consistency_review(
		SessionStore(),
		ScanRegistry(),
		snapshots,
		{'snapshot_id': rec.snapshot_id},
	)
	assert result['ok'] is True
	assert 'summary' in result['data']


async def test_build_snapshot_returns_existing() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	snapshots = SnapshotRegistry()
	rec = snapshots.register(snapshot=snapshot.to_dict(), url=snapshot.url)

	result = await handle_build_design_snapshot(
		SessionStore(),
		ScanRegistry(),
		snapshots,
		{'snapshot_id': rec.snapshot_id},
	)
	assert result['ok'] is True
	assert result['data']['snapshot_id'] == rec.snapshot_id


def main() -> int:
	asyncio.run(test_design_review_from_snapshot_id())
	asyncio.run(test_consistency_review_from_snapshot_id())
	asyncio.run(test_build_snapshot_returns_existing())
	print('design mcp handlers: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
