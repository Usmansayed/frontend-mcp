"""Community Duplication Pipeline tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

import asyncio
from unittest.mock import patch

from navigation.figma_intelligence.community_duplication.api_loader import (
	build_design_snapshot,
	official_to_extraction,
)
from navigation.figma_intelligence.community_duplication.file_key_resolver import (
	content_id_from_url,
	file_key_from_url,
	resolve_content_id,
	resolve_file_key_from_payload,
)
from navigation.figma_intelligence.community_duplication.models import (
	DuplicationRequest,
	OfficialFilePayload,
)
from navigation.figma_intelligence.community_duplication.orchestrator import (
	CommunityDuplicationOrchestrator,
)
from navigation.figma_intelligence.discovery.community_adapter.backends.http import (
	_parse_search_results,
)
from navigation.figma_intelligence.models import FigmaCandidate


def test_file_key_from_design_url() -> None:
	url = 'https://www.figma.com/design/AbCdEfGhIjKlMnOpQrStUv/Title'
	assert file_key_from_url(url) == 'AbCdEfGhIjKlMnOpQrStUv'


def test_content_id_from_community_url() -> None:
	url = 'https://www.figma.com/community/file/1202426685198179521/saas'
	assert content_id_from_url(url) == '1202426685198179521'


def test_resolve_content_id_from_metadata() -> None:
	assert resolve_content_id(metadata={'content_id': '999'}) == '999'


def test_resolve_file_key_from_duplicate_payload() -> None:
	payload = {
		'meta': {
			'key': 'XyZ1234567890AbCdEfGh',
			'url': 'https://www.figma.com/design/XyZ1234567890AbCdEfGh/Copy',
		}
	}
	key, draft = resolve_file_key_from_payload(payload)
	assert key == 'XyZ1234567890AbCdEfGh'
	assert 'design' in draft


def test_parse_search_results_content_id() -> None:
	results = [
		{
			'model': {
				'id': 'uuid-1',
				'name': 'Test Dashboard',
				'content_id': '1234567890',
				'community_rdp_url': 'https://www.figma.com/community/file/1234567890',
				'like_count': 10,
				'user_count': 100,
				'creator': {'handle': 'author'},
			}
		}
	]
	hits = _parse_search_results(results, max_results=5)
	assert len(hits) == 1
	assert hits[0].extra['content_id'] == '1234567890'
	assert hits[0].title == 'Test Dashboard'


def test_official_to_extraction_and_snapshot() -> None:
	official = OfficialFilePayload(
		file_key='TestKey1234567890Ab',
		document={
			'id': '0:0',
			'name': 'Page',
			'type': 'DOCUMENT',
			'children': [
				{
					'id': '1:1',
					'name': 'Frame',
					'type': 'FRAME',
					'layoutMode': 'VERTICAL',
					'children': [],
				}
			],
		},
		components={'1:1': {'name': 'Frame'}},
		styles={'s1': {'name': 'Primary'}},
		metadata={'name': 'Test File'},
	)
	ext = official_to_extraction(official, candidate_id='c1')
	assert ext.provider_id == 'official_figma_rest'
	assert ext.components
	snap = build_design_snapshot(ext)
	assert snap['source_stage'] == 'community_duplication_pipeline'
	assert snap['file_key'] == 'TestKey1234567890Ab'


def test_orchestrator_preexisting_file_key() -> None:
	candidate = FigmaCandidate(
		candidate_id='c1',
		title='Owned',
		source='community',
		provider_id='',
		file_key='ExistingKey1234567890',
	)
	req = DuplicationRequest(candidate=candidate, pat='dummy-pat')

	mock_official = OfficialFilePayload(
		file_key='ExistingKey1234567890',
		document={'id': '0:0', 'type': 'DOCUMENT', 'children': []},
		metadata={'name': 'Owned'},
	)

	with patch(
		'navigation.figma_intelligence.community_duplication.orchestrator.load_official_file',
		return_value=mock_official,
	):
		result = asyncio.run(CommunityDuplicationOrchestrator().run(req))

	assert result.duplication.method == 'preexisting_file_key'
	assert result.duplication.file_key == 'ExistingKey1234567890'
	assert result.extraction is not None
	assert result.design_snapshot
