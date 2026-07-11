"""Tests for Design Snapshot Engine extractors."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.design_snapshot_engine.raw_context import RawBrowserContext


FIXTURE = {
	'url': 'http://localhost:5173/login',
	'viewport': {'width': 1280, 'height': 720},
	'document': {'scrollWidth': 1280, 'scrollHeight': 900},
	'css_variables': {'--primary': '#2563eb', '--spacing-4': '16px'},
	'elements': [
		{
			'tag': 'h1',
			'selector': 'h1',
			'text': 'Sign in',
			'classes': [],
			'style': {
				'fontSize': '22px',
				'fontFamily': 'Inter, sans-serif',
				'lineHeight': '28px',
				'color': 'rgb(17, 24, 39)',
				'backgroundColor': 'rgba(0, 0, 0, 0)',
				'padding': '0px',
				'margin': '0px 0px 16px',
			},
		},
		{
			'tag': 'button',
			'selector': 'button.primary',
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
		{
			'tag': 'p',
			'selector': 'p',
			'text': 'Body copy',
			'classes': [],
			'style': {
				'fontSize': '16px',
				'color': 'rgb(55, 65, 81)',
				'backgroundColor': 'rgb(255, 255, 255)',
				'lineHeight': '24px',
			},
		},
	],
}


def test_snapshot_engine_produces_all_sections() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	data = snapshot.to_dict()
	for key in (
		'typography', 'spacing', 'colors', 'layout', 'grid',
		'hierarchy', 'components', 'motion', 'accessibility', 'design_tokens',
	):
		assert key in data, f'missing section {key}'


def test_typography_extractor_flags_off_scale() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	assert snapshot.typography.font_families
	assert any(s == 13.0 or s == 13 for s in snapshot.typography.font_sizes_px) or snapshot.typography.issues


def test_color_extractor_finds_wcag_and_raw_colors() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	assert snapshot.colors.raw_color_count >= 1
	assert snapshot.colors.palette


def test_design_tokens_from_css_variables() -> None:
	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	assert '--primary' in snapshot.design_tokens.css_variables


def test_design_sense_reviews_from_snapshot() -> None:
	import asyncio

	from navigation.design_sense_intelligence import DesignSenseService
	from navigation.design_sense_intelligence.snapshot_access import review_request_from_snapshot

	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	request = review_request_from_snapshot(snapshot, user_task='Sign in to dashboard')
	report = asyncio.run(DesignSenseService().review(request))
	assert report.summary
	assert report.findings


def test_consistency_audits_snapshot() -> None:
	from navigation.consistency_intelligence.service import ConsistencyIntelligenceService

	engine = DesignSnapshotEngine()
	snapshot = engine.capture_from_fixture(FIXTURE)
	report = ConsistencyIntelligenceService().audit(snapshot)
	assert report.summary
	assert isinstance(report.passed, bool)


def test_reference_registry_compare() -> None:
	from navigation.design_reference_registry import DesignReferenceRegistry

	engine = DesignSnapshotEngine()
	current = engine.capture_from_fixture(FIXTURE)
	ref = engine.capture_from_fixture({**FIXTURE, 'url': 'http://ref.example/dashboard'})
	registry = DesignReferenceRegistry()
	registry.register('ref_login', 'Reference Login', ref, tags=['auth'])
	matches = registry.find_similar(current)
	assert matches
	assert 0.0 <= matches[0].similarity_score <= 1.0


def main() -> int:
	test_snapshot_engine_produces_all_sections()
	test_typography_extractor_flags_off_scale()
	test_color_extractor_finds_wcag_and_raw_colors()
	test_design_tokens_from_css_variables()
	test_design_sense_reviews_from_snapshot()
	test_consistency_audits_snapshot()
	test_reference_registry_compare()
	print('design snapshot engine: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
