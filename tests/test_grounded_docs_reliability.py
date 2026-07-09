"""Reliability tests for Grounded Docs cross-platform helpers."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
	sys.path.insert(0, str(SRC))

from navigation.framework_intelligence.providers.grounded_docs.normalize import normalize_search_response
from navigation.framework_intelligence.providers.grounded_docs.registry import LIBRARY_SPECS
from navigation.framework_intelligence.providers.grounded_docs.runtime import (
	default_store_path,
	parse_node_major_version,
)
from navigation.framework_intelligence.models import ProjectMetadata


def test_parse_node_major_version() -> None:
	assert parse_node_major_version('v24.7.0') == 24
	assert parse_node_major_version('22.1.0') == 22
	assert parse_node_major_version('invalid') is None


def test_default_store_path_prefers_env() -> None:
	import os

	old = os.environ.get('GROUNDED_DOCS_STORE_PATH')
	custom = str(ROOT / 'tmp-custom-store')
	try:
		os.environ['GROUNDED_DOCS_STORE_PATH'] = custom
		path = default_store_path('/repo')
		assert str(path).replace('\\', '/') == custom.replace('\\', '/')
	finally:
		if old is None:
			os.environ.pop('GROUNDED_DOCS_STORE_PATH', None)
		else:
			os.environ['GROUNDED_DOCS_STORE_PATH'] = old


def test_default_store_path_uses_repo() -> None:
	path = default_store_path(str(ROOT / 'sandbox'))
	assert path.name == 'grounded-docs-store'
	assert path.parent.name == 'artifacts'


def test_normalize_list_response() -> None:
	spec = LIBRARY_SPECS['react']
	meta = ProjectMetadata(repo_root=str(ROOT / 'sandbox'), framework='React', framework_version='18.3')
	raw = [{'url': 'https://react.dev/x.md', 'content': 'useEffect cleanup docs'}]
	result = normalize_search_response(
		raw,
		provider='grounded_docs',
		spec=spec,
		metadata=meta,
		topic='useEffect',
	)
	assert 'useEffect cleanup docs' in result.content
	assert result.citations == ['https://react.dev/x.md']


def test_normalize_empty_list() -> None:
	spec = LIBRARY_SPECS['react']
	meta = ProjectMetadata(repo_root=str(ROOT / 'sandbox'), framework='React')
	result = normalize_search_response(
		[],
		provider='grounded_docs',
		spec=spec,
		metadata=meta,
		topic='hooks',
	)
	assert result.content == ''


def main() -> int:
	test_parse_node_major_version()
	test_default_store_path_prefers_env()
	test_default_store_path_uses_repo()
	test_normalize_list_response()
	test_normalize_empty_list()
	print('grounded docs reliability: PASS')
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
