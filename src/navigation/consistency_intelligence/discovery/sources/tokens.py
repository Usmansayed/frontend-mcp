"""Declared tokens knowledge source — DTCG, CSS variables, Tailwind theme."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from navigation.consistency_intelligence.discovery.collect_helpers import build_scale_cluster, confidence_from_support
from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment
from navigation.consistency_intelligence.graph.model import TokenNode

_TOKEN_FILENAMES = frozenset({
	'tokens.json',
	'design-tokens.json',
	'design_tokens.json',
})
_CSS_VAR_RE = re.compile(r'--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);')
_SKIP_DIRS = frozenset({
	'node_modules', '.git', 'dist', 'build', '.next', 'coverage', '__pycache__', '.perception',
})


class TokensKnowledgeSource:
	source_id = 'tokens'

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		root = ctx.repo_root
		if root is None or not root.is_dir():
			return KnowledgeFragment(
				source_id=self.source_id,
				degraded=['tokens_missing_repo_root'],
			)

		tokens: list[TokenNode] = []
		evidence: list[dict[str, Any]] = []
		degraded: list[str] = []

		dtcg_files = _find_dtcg_files(root)
		for path in dtcg_files[:8]:
			try:
				data = json.loads(path.read_text(encoding='utf-8'))
			except (OSError, json.JSONDecodeError):
				degraded.append(f'tokens_parse_error:{path.name}')
				continue
			found = _flatten_dtcg(data, prefix=())
			tokens.extend(found)
			evidence.append({'kind': 'dtcg_file', 'path': str(path.relative_to(root))})

		css_files = _find_css_token_files(root)
		for path in css_files[:6]:
			try:
				text = path.read_text(encoding='utf-8', errors='ignore')
			except OSError:
				continue
			for match in _CSS_VAR_RE.finditer(text):
				var_name, var_value = match.group(1), match.group(2).strip()
				tokens.append(
					TokenNode(
						path=tuple(var_name.split('-')),
						value=var_value,
						resolved_value=var_value,
						layer='semantic',
						source='css',
						provenance='declared',
						confidence=1.0,
						extensions={'file': str(path.relative_to(root))},
					)
				)
			evidence.append({'kind': 'css_variables', 'path': str(path.relative_to(root))})

		tailwind = _find_tailwind_config(root)
		if tailwind:
			tw_tokens, tw_evidence = _parse_tailwind_theme(tailwind, root)
			tokens.extend(tw_tokens)
			evidence.extend(tw_evidence)

		# Attach scale hints from numeric CSS vars
		spacing_vals = [
			float(t.resolved_value.replace('px', ''))
			for t in tokens
			if isinstance(t.resolved_value, str) and t.resolved_value.endswith('px')
			and 'spacing' in t.path_str
		]
		scale_evidence: list[dict[str, Any]] = []
		if spacing_vals:
			cluster = build_scale_cluster('spacing', spacing_vals)
			if cluster:
				scale_evidence.append({'kind': 'spacing_scale', 'cluster': cluster.to_dict()})

		if not tokens:
			degraded.append('tokens_none_found')

		confidence = 1.0 if any(t.provenance == 'declared' for t in tokens) else confidence_from_support(len(tokens))

		return KnowledgeFragment(
			source_id=self.source_id,
			tokens=tokens,
			evidence=[*evidence, *scale_evidence],
			confidence=confidence,
			degraded=degraded,
		)


def _find_dtcg_files(root: Path) -> list[Path]:
	found: list[Path] = []
	for path in root.rglob('*.json'):
		if any(part in _SKIP_DIRS for part in path.parts):
			continue
		if path.name in _TOKEN_FILENAMES or path.name.endswith('.tokens.json'):
			found.append(path)
	return found


def _find_css_token_files(root: Path) -> list[Path]:
	candidates: list[Path] = []
	for path in root.rglob('*.css'):
		if any(part in _SKIP_DIRS for part in path.parts):
			continue
		name = path.name.lower()
		if name in ('globals.css', 'variables.css', 'tokens.css', 'theme.css') or 'token' in name:
			candidates.append(path)
	return candidates


def _find_tailwind_config(root: Path) -> Path | None:
	for name in ('tailwind.config.ts', 'tailwind.config.js', 'tailwind.config.mjs', 'tailwind.config.cjs'):
		for path in root.rglob(name):
			if any(part in _SKIP_DIRS for part in path.parts):
				continue
			return path
	return None


def _flatten_dtcg(data: dict[str, Any], *, prefix: tuple[str, ...]) -> list[TokenNode]:
	out: list[TokenNode] = []
	for key, value in data.items():
		if key.startswith('$'):
			continue
		path = (*prefix, str(key))
		if isinstance(value, dict):
			if '$value' in value or 'value' in value:
				raw = value.get('$value', value.get('value'))
				dtcg_type = value.get('$type') or value.get('type')
				out.append(
					TokenNode(
						path=path,
						dtcg_type=str(dtcg_type) if dtcg_type else None,
						value=raw,
						resolved_value=raw,
						layer='primitive' if len(path) <= 2 else 'semantic',
						source='dtcg',
						provenance='declared',
						confidence=1.0,
					)
				)
			else:
				out.extend(_flatten_dtcg(value, prefix=path))
	return out


def _parse_tailwind_theme(path: Path, root: Path) -> tuple[list[TokenNode], list[dict[str, Any]]]:
	text = path.read_text(encoding='utf-8', errors='ignore')
	tokens: list[TokenNode] = []
	evidence = [{'kind': 'tailwind_config', 'path': str(path.relative_to(root))}]

	for section, pattern in (
		('color', r'colors\s*:\s*\{([^}]+)\}'),
		('spacing', r'spacing\s*:\s*\{([^}]+)\}'),
		('borderRadius', r'borderRadius\s*:\s*\{([^}]+)\}'),
	):
		match = re.search(pattern, text, re.DOTALL)
		if not match:
			continue
		block = match.group(1)
		for entry in re.finditer(r'["\']?([a-zA-Z0-9_-]+)["\']?\s*:\s*["\']([^"\']+)["\']', block):
			name, value = entry.group(1), entry.group(2)
			tokens.append(
				TokenNode(
					path=('tailwind', section, name),
					value=value,
					resolved_value=value,
					layer='semantic',
					source='tailwind',
					provenance='declared',
					confidence=1.0,
				)
			)
	return tokens, evidence
