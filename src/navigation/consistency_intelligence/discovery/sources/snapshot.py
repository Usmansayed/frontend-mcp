"""Design Snapshot knowledge source — Browser Intelligence → DesignSnapshot."""
from __future__ import annotations

from typing import Any

import re

from navigation.consistency_intelligence.discovery.collect_helpers import (
	build_scale_cluster,
	build_standard,
	infer_component_from_node,
	pattern_from_snapshot,
	standard_id,
)
from navigation.consistency_intelligence.discovery.context import DiscoveryContext
from navigation.consistency_intelligence.discovery.sources.protocol import KnowledgeFragment
from navigation.consistency_intelligence.graph.model import (
	ComponentNode,
	RelationshipEdge,
	StandardNode,
	TokenNode,
)
from navigation.design_snapshot_engine.models import DesignSnapshot

_VAR_RE = re.compile(r'var\(\s*--([a-zA-Z0-9_-]+)')


class SnapshotKnowledgeSource:
	source_id = 'snapshot'

	async def collect(self, ctx: DiscoveryContext) -> KnowledgeFragment:
		snapshot = ctx.design_snapshot
		if snapshot is None:
			return KnowledgeFragment(
				source_id=self.source_id,
				degraded=['snapshot_missing: pass design_snapshot in DiscoveryContext'],
			)

		if isinstance(snapshot, dict):
			snapshot = DesignSnapshot.from_dict(snapshot)

		return _collect_from_snapshot(snapshot, scan_id=ctx.scan_id)


def _collect_from_snapshot(snapshot: DesignSnapshot, *, scan_id: str | None = None) -> KnowledgeFragment:
	degraded: list[str] = list(snapshot.degraded)
	standards: list[StandardNode] = []
	tokens: list[TokenNode] = []
	components: dict[str, ComponentNode] = {}
	patterns: dict[str, Any] = {}
	relationships: list[RelationshipEdge] = []
	evidence: list[dict[str, Any]] = []

	url = snapshot.url or 'unknown'
	evidence.append({'kind': 'snapshot', 'url': url, 'scan_id': scan_id or snapshot.scan_id})

	# Typography
	if snapshot.typography.font_families:
		std = build_standard(
			context='typography',
			property_name='font-family',
			values=snapshot.typography.font_families,
			category='typography',
			evidence_sample=snapshot.typography.font_families[:4],
		)
		if std:
			standards.append(std)

	if snapshot.typography.font_sizes_px:
		cluster = build_scale_cluster('font-size', snapshot.typography.font_sizes_px)
		if cluster:
			evidence.append({'kind': 'typography_scale', 'cluster': cluster.to_dict()})
		for size in snapshot.typography.font_sizes_px[:6]:
			std = build_standard(
				context='typography',
				property_name='font-size',
				values=[f'{size}px'],
				category='typography',
			)
			if std:
				standards.append(std)

	# Spacing
	all_spacing = (
		snapshot.spacing.padding_values_px
		+ snapshot.spacing.margin_values_px
		+ snapshot.spacing.gap_values_px
	)
	if all_spacing:
		cluster = build_scale_cluster('spacing', all_spacing)
		if cluster:
			evidence.append({'kind': 'spacing_scale', 'cluster': cluster.to_dict()})
		std = build_standard(
			context='spacing',
			property_name='scale',
			values=[f'{v}px' for v in all_spacing],
			category='spacing',
		)
		if std:
			standards.append(std)

	if snapshot.spacing.base_unit_px is not None:
		standards.append(
			StandardNode(
				id=standard_id('spacing', 'base-unit'),
				category='spacing',
				context='spacing',
				property='base-unit',
				expected_values=[f'{snapshot.spacing.base_unit_px}px'],
				confidence=0.85,
				support_count=1,
				provenance='learned',
			)
		)

	# Colors → learned tokens
	for idx, color in enumerate(snapshot.colors.text_colors[:12]):
		tokens.append(
			TokenNode(
				path=('color', 'text', str(idx)),
				dtcg_type='color',
				value=color,
				resolved_value=color,
				layer='semantic',
				source='snapshot',
				provenance='learned',
				confidence=0.7,
			)
		)
	for idx, color in enumerate(snapshot.colors.background_colors[:12]):
		tokens.append(
			TokenNode(
				path=('color', 'background', str(idx)),
				dtcg_type='color',
				value=color,
				resolved_value=color,
				layer='semantic',
				source='snapshot',
				provenance='learned',
				confidence=0.7,
			)
		)
	for idx, entry in enumerate(snapshot.colors.palette[:16]):
		name = str(entry.get('hex') or entry.get('color') or idx)
		value = entry.get('hex') or entry.get('color') or ''
		if value:
			tokens.append(
				TokenNode(
					path=('color', 'palette', name.replace('#', '')),
					dtcg_type='color',
					value=value,
					resolved_value=value,
					layer='primitive',
					source='snapshot',
					provenance='learned',
					confidence=0.75,
				)
			)

	# Design token CSS variables from snapshot
	for var_name, var_value in list(snapshot.design_tokens.css_variables.items())[:40]:
		path = tuple(var_name.lstrip('-').split('-'))
		tokens.append(
			TokenNode(
				path=path,
				value=var_value,
				resolved_value=var_value,
				layer='semantic',
				source='snapshot',
				provenance='learned',
				confidence=0.8,
			)
		)

	# Components from interactive nodes
	for node in snapshot.components.nodes:
		name, variants = infer_component_from_node(node)
		key = name.lower()
		comp = components.get(key) or ComponentNode(name=name, support_count=0, confidence=0.0)
		comp.support_count += 1
		for v in variants:
			if v not in comp.variants:
				comp.variants.append(v)
		style = node.get('style') or {}
		padding = style.get('padding') or style.get('paddingTop')
		if padding:
			std = build_standard(
				context=name,
				property_name='padding',
				values=[str(padding)],
				category='spacing',
				evidence_sample=[node.get('selector', '')],
			)
			if std:
				comp.standards.append(std)
		for prop_key, css_val in style.items():
			for var_match in _VAR_RE.findall(str(css_val)):
				token_path = '.'.join(var_match.split('-'))
				relationships.append(
					RelationshipEdge(
						kind='uses_token',
						source=node.get('selector', name),
						target=token_path,
					)
				)
		font_size = style.get('fontSize')
		if font_size:
			std = build_standard(
				context=name,
				property_name='font-size',
				values=[str(font_size)],
				category='typography',
			)
			if std:
				comp.standards.append(std)
		border_radius = style.get('borderRadius')
		if border_radius:
			std = build_standard(
				context=name,
				property_name='border-radius',
				values=[str(border_radius)],
				category='radius',
			)
			if std:
				comp.standards.append(std)
				radius_vals = _parse_px_list(str(border_radius))
				if radius_vals:
					cluster = build_scale_cluster('border-radius', radius_vals)
					if cluster:
						evidence.append({'kind': 'radius_scale', 'cluster': cluster.to_dict()})

		comp.confidence = min(0.99, 0.5 + comp.support_count * 0.1)
		if comp.variants and not comp.canonical_variant:
			comp.canonical_variant = comp.variants[0]
		components[key] = comp
		relationships.append(
			RelationshipEdge(kind='observed_in', source=f'component:{name}', target=url, metadata={'scan_id': scan_id})
		)

	# UI patterns
	for pattern in snapshot.components.patterns:
		pname = str(pattern.get('name') or '')
		count = int(pattern.get('count') or 0)
		if pname and count > 0:
			patterns[pname.lower()] = pattern_from_snapshot(pname, count)

	# Form controls as component evidence
	for control in snapshot.components.form_controls[:20]:
		tag = str(control.get('tag') or 'input')
		key = tag.lower()
		comp = components.get(key) or ComponentNode(name=tag, support_count=0)
		comp.support_count += 1
		comp.confidence = min(0.99, 0.5 + comp.support_count * 0.08)
		components[key] = comp

	confidence = 0.0
	if standards or components or tokens:
		confidence = min(0.95, 0.55 + len(standards) * 0.02 + len(components) * 0.05)

	if not standards and not components and not tokens:
		degraded.append('snapshot_empty: no extractable design knowledge')

	return KnowledgeFragment(
		source_id='snapshot',
		standards=standards,
		tokens=tokens,
		components=components,
		patterns=patterns,
		relationships=relationships,
		evidence=evidence,
		confidence=confidence,
		degraded=degraded,
	)


def _parse_px_list(value: str) -> list[float]:
	out: list[float] = []
	for part in value.replace(',', ' ').split():
		part = part.strip()
		if part.endswith('px'):
			try:
				out.append(float(part[:-2]))
			except ValueError:
				continue
	return out
