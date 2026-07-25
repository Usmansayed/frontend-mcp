"""UX Knowledge Brain ↔ Design Sense provider integration."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from navigation.design_sense_intelligence.models import ReviewRequest
from navigation.design_sense_intelligence.providers.ux_knowledge import (
	UxKnowledgeProvider,
	build_retrieval_params,
)


def test_map_checkout_task() -> None:
	params = build_retrieval_params(ReviewRequest(user_task='Complete checkout'))
	assert params is not None
	assert params['surface_type'] == 'checkout'
	assert params['user_flow'] == 'checkout'


def test_map_dashboard_url() -> None:
	params = build_retrieval_params(
		ReviewRequest(user_task='Review metrics', preview_url='http://localhost:5173/dashboard')
	)
	assert params is not None
	assert params['surface_type'] == 'dashboard'


def test_map_forms_from_login() -> None:
	params = build_retrieval_params(ReviewRequest(user_task='Sign in with password'))
	assert params is not None
	assert params['surface_type'] == 'forms'


def test_map_psychology_cognitive_load() -> None:
	params = build_retrieval_params(
		ReviewRequest(user_task="Reduce cognitive load and Hick choice overload")
	)
	assert params is not None
	assert params.get("psychology_category") == "cognitive_load"


def test_ux_knowledge_provider_contributes_from_corpus() -> None:
	async def _run() -> None:
		provider = UxKnowledgeProvider()
		contrib = await provider.contribute(
			ReviewRequest(
				user_task='Build SaaS analytics dashboard with sidebar',
				repo_root=str(ROOT),
			)
		)
		assert contrib.provider == 'ux_knowledge'
		assert 'ux_knowledge_structured' in contrib.degraded or 'ux_knowledge_no_match' in contrib.degraded
		if 'ux_knowledge_structured' in contrib.degraded:
			assert any(n.startswith('ux_kb:playbook:') for n in contrib.notes)
			assert any(f.source == 'ux_knowledge' for f in contrib.findings)
			assert any(f.metadata.get('principle_id') for f in contrib.findings)

	asyncio.run(_run())


def test_ux_knowledge_provider_falls_back_to_packaged_corpus() -> None:
	"""Missing repo ForOpenCode must still retrieve from wheel-packaged data."""

	async def _run() -> None:
		provider = UxKnowledgeProvider()
		contrib = await provider.contribute(
			ReviewRequest(
				user_task='Landing hero CTA',
				repo_root=str(ROOT / 'does_not_exist_corpus'),
			)
		)
		assert 'ux_knowledge_missing_corpus' not in contrib.degraded
		assert 'ux_knowledge_structured' in contrib.degraded or 'ux_knowledge_no_match' in contrib.degraded
		assert any(n.startswith('ux_kb:corpus:packaged') for n in contrib.notes) or any(
			n.startswith('ux_kb:playbook:') for n in contrib.notes
		)

	asyncio.run(_run())


def main() -> int:
	test_map_checkout_task()
	test_map_dashboard_url()
	test_map_forms_from_login()
	test_map_psychology_cognitive_load()
	test_ux_knowledge_provider_contributes_from_corpus()
	test_ux_knowledge_provider_falls_back_to_packaged_corpus()
	print('ux_knowledge design sense: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
