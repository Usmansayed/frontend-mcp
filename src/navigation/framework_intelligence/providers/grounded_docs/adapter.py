"""Grounded Docs documentation provider — adapter over upstream CLI."""
from __future__ import annotations

from ...models import DocumentationResult, ProjectMetadata
from ..documentation import DocumentationProviderError
from .client import GroundedDocsCli, GroundedDocsCliError
from .normalize import normalize_search_response
from .query_builder import build_search_query
from .registry import GroundedDocsLibrarySpec, resolve_library_spec
from .runtime import default_store_path, ensure_store_dir


class GroundedDocsProvider:
	name = 'grounded_docs'

	def __init__(self, *, cli: GroundedDocsCli | None = None) -> None:
		self._cli = cli or GroundedDocsCli()

	def _cli_for(self, metadata: ProjectMetadata) -> GroundedDocsCli:
		if self._cli._store_path is not None:
			store_path = ensure_store_dir(self._cli._store_path)
			return GroundedDocsCli(
				cli_path=self._cli._cli_path,
				store_path=store_path,
				scrape_timeout_s=self._cli._scrape_timeout_s,
				search_timeout_s=self._cli._search_timeout_s,
			)
		store_path = default_store_path(metadata.repo_root or None)
		return GroundedDocsCli(
			cli_path=self._cli._cli_path,
			store_path=store_path,
			scrape_timeout_s=self._cli._scrape_timeout_s,
			search_timeout_s=self._cli._search_timeout_s,
		)

	async def fetch_documentation(
		self,
		metadata: ProjectMetadata,
		*,
		topic: str,
	) -> DocumentationResult:
		cli = self._cli_for(metadata)
		if not cli.available():
			major = cli._read_node_major_version()
			if major is not None and major < 22:
				raise DocumentationProviderError(f'node_version_too_old:{major}')
			raise DocumentationProviderError('grounded_docs_cli_unavailable')

		spec = resolve_library_spec(metadata.primary_package, metadata.framework)
		if spec is None:
			raise DocumentationProviderError('library_spec_not_found')

		query = build_search_query(metadata, topic)
		version = metadata.framework_version
		raw = await self._search_with_on_demand_scrape(cli, spec, query, version=version)
		result = normalize_search_response(
			raw,
			provider=self.name,
			spec=spec,
			metadata=metadata,
			topic=topic,
		)
		if not result.content.strip():
			raise DocumentationProviderError('docs_empty_result')
		return result

	async def _search_with_on_demand_scrape(
		self,
		cli: GroundedDocsCli,
		spec: GroundedDocsLibrarySpec,
		query: str,
		*,
		version: str | None,
	) -> object:
		try:
			return await cli.search(spec.library, query, version=version)
		except GroundedDocsCliError as exc:
			if not str(exc).startswith('library_not_indexed'):
				raise DocumentationProviderError(str(exc)) from exc
			await cli.scrape(spec.library, spec.default_source_url, version=version)
			try:
				return await cli.search(spec.library, query, version=version)
			except GroundedDocsCliError as retry_exc:
				raise DocumentationProviderError(str(retry_exc)) from retry_exc
