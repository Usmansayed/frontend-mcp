"""Codebase knowledge source — React, Vue, Svelte component patterns."""
from __future__ import annotations

import re
from pathlib import Path

from navigation.consistency_intelligence.discovery.collect_helpers import build_standard, confidence_from_support
from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment
from navigation.consistency_intelligence.graph.model import ComponentNode, RelationshipEdge

_COMPONENT_EXTENSIONS = frozenset({'.tsx', '.jsx', '.vue', '.svelte'})
_SKIP_DIRS = frozenset({
	'node_modules', '.git', 'dist', 'build', '.next', '.nuxt', 'coverage',
	'__pycache__', '.perception', 'vendor', '.turbo', '.cache',
})
_EXPORT_RE = re.compile(
	r'export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z][A-Za-z0-9_]*)',
)
_VARIANT_RE = re.compile(
	r"""['"](primary|secondary|ghost|outline|destructive|default|sm|md|lg)['"]""",
	re.IGNORECASE,
)
_VARIANT_PROP_RE = re.compile(r'variant\s*[=:]\s*["\']([a-zA-Z0-9_-]+)["\']')


class CodebaseKnowledgeSource:
	source_id = 'codebase'

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		root = ctx.repo_root
		if root is None or not root.is_dir():
			return KnowledgeFragment(
				source_id=self.source_id,
				degraded=['codebase_missing_repo_root'],
			)

		components: dict[str, ComponentNode] = {}
		relationships: list[RelationshipEdge] = []
		evidence: list[dict] = []
		files_scanned = 0

		for path in _iter_component_files(root):
			files_scanned += 1
			try:
				text = path.read_text(encoding='utf-8', errors='ignore')
			except OSError:
				continue
			names = _EXPORT_RE.findall(text)
			variants = list(dict.fromkeys(_VARIANT_RE.findall(text) + _VARIANT_PROP_RE.findall(text)))
			rel_path = str(path.relative_to(root)).replace('\\', '/')

			for name in names:
				if not _looks_like_component(name):
					continue
				key = name.lower()
				comp = components.get(key) or ComponentNode(name=name, support_count=0, confidence=0.0)
				comp.support_count += 1
				for v in variants:
					if v.lower() not in [x.lower() for x in comp.variants]:
						comp.variants.append(v)
				comp.confidence = confidence_from_support(comp.support_count, base=0.6)
				if comp.variants and not comp.canonical_variant:
					comp.canonical_variant = comp.variants[0]
				components[key] = comp
				relationships.append(
					RelationshipEdge(
						kind='defined_in',
						source=f'component:{name}',
						target=rel_path,
					)
				)

			ui_std = build_standard(
				context=_infer_ui_context(path.name),
				property_name='file',
				values=[rel_path],
				category='codebase',
				provenance='learned',
			)
			if ui_std and _is_ui_file(path.name):
				# Track UI file presence as weak evidence
				evidence.append({'kind': 'ui_file', 'path': rel_path})

		degraded: list[str] = []
		if files_scanned == 0:
			degraded.append('codebase_no_component_files_found')
		confidence = confidence_from_support(len(components), base=0.55) if components else 0.0

		evidence.append({'kind': 'codebase_scan', 'files_scanned': files_scanned, 'components_found': len(components)})

		return KnowledgeFragment(
			source_id=self.source_id,
			components=components,
			relationships=relationships,
			evidence=evidence,
			confidence=confidence,
			degraded=degraded,
		)


def _iter_component_files(root: Path):
	for path in root.rglob('*'):
		if not path.is_file():
			continue
		if path.suffix not in _COMPONENT_EXTENSIONS:
			continue
		if any(part in _SKIP_DIRS for part in path.parts):
			continue
		yield path


def _looks_like_component(name: str) -> bool:
	if len(name) < 2:
		return False
	if name.endswith(('Provider', 'Context', 'Hook', 'Utils', 'Helper', 'Config', 'Type', 'Types')):
		return False
	return name[0].isupper()


def _is_ui_file(filename: str) -> bool:
	lower = filename.lower()
	return any(token in lower for token in ('button', 'card', 'input', 'form', 'nav', 'modal', 'dialog'))


def _infer_ui_context(filename: str) -> str:
	lower = filename.lower()
	for token in ('button', 'card', 'input', 'form', 'nav', 'modal', 'dialog', 'select'):
		if token in lower:
			return token
	stem = Path(filename).stem
	return stem.lower() if stem else 'component'
