"""Bridge DesignSnapshot ↔ ReviewRequest for reasoning-only Design Sense."""
from __future__ import annotations

from typing import Any

from navigation.design_snapshot_engine.models import DesignSnapshot

from .models import ReviewRequest


def resolve_snapshot(request: ReviewRequest) -> DesignSnapshot | None:
	if request.design_snapshot is not None:
		return request.design_snapshot
	if request._legacy_snapshot_dict:
		return DesignSnapshot.from_dict(request._legacy_snapshot_dict)
	return None


def enrich_request(request: ReviewRequest) -> ReviewRequest:
	"""Populate legacy fields from snapshot for backward-compatible reviewers."""
	snapshot = resolve_snapshot(request)
	if snapshot is None:
		return request

	if not request.visual_insights and snapshot.layout.visual_insights:
		request.visual_insights = snapshot.layout.visual_insights
	elif not request.visual_insights and snapshot.layout.issues:
		request.visual_insights = {
			'issues': snapshot.layout.issues,
			'element_boxes': snapshot.layout.interactive_boxes,
		}

	if not request.computed_styles:
		request.computed_styles = snapshot_to_computed_styles(snapshot)

	if not request.design_tokens:
		request.design_tokens = {
			'spacing': snapshot.design_tokens.spacing_scale,
			'radius': snapshot.design_tokens.radius_scale,
			'typography': snapshot.design_tokens.typography_scale,
			'css_variables': snapshot.design_tokens.css_variables,
			'color_tokens': snapshot.design_tokens.color_tokens,
		}

	if not request.preview_url and snapshot.url:
		request.preview_url = snapshot.url
	if not request.scan_id and snapshot.scan_id:
		request.scan_id = snapshot.scan_id
	if not request.screenshot_ref:
		request.screenshot_ref = snapshot.provenance.get('screenshot_ref')

	if not request.dom_snapshot:
		request.dom_snapshot = {
			'url': snapshot.url,
			'captured_at': snapshot.captured_at,
			'typography_families': snapshot.typography.font_families,
			'color_palette_size': len(snapshot.colors.palette),
			'component_patterns': snapshot.components.patterns,
		}

	if request.project_design_knowledge is None and request.repo_root and snapshot.url:
		from navigation.consistency_intelligence.integrations.design_sense import load_project_design_knowledge

		request.project_design_knowledge = load_project_design_knowledge(
			repo_root=request.repo_root,
			url=snapshot.url,
		)
		if request.project_design_knowledge and request.dom_snapshot is not None:
			request.dom_snapshot['project_design_knowledge'] = request.project_design_knowledge

	return request


def snapshot_to_computed_styles(snapshot: DesignSnapshot) -> list[dict[str, Any]]:
	"""Flatten snapshot sections into design-lint compatible style rows."""
	rows: list[dict[str, Any]] = []
	for sample in snapshot.typography.body_samples:
		rows.append({
			'selector': sample.get('tag', 'p'),
			'tag': sample.get('tag', 'p'),
			'text': sample.get('text', ''),
			'style': {
				'fontSize': f"{sample.get('font_size_px')}px" if sample.get('font_size_px') else None,
				'lineHeight': f"{sample.get('line_height_px')}px" if sample.get('line_height_px') else None,
			},
			'classes': [],
		})
	for node in snapshot.components.nodes[:12]:
		style = node.get('style') if isinstance(node.get('style'), dict) else {}
		rows.append({
			'selector': node.get('tag', 'button'),
			'tag': node.get('tag', 'button'),
			'text': node.get('text', ''),
			'classes': node.get('classes', []),
			'style': style,
		})
	# Rebuild from provenance element samples when available
	for el in snapshot.provenance.get('elements') or []:
		if isinstance(el, dict) and el.get('style'):
			rows.append({
				'selector': el.get('selector', ''),
				'tag': el.get('tag', 'div'),
				'text': el.get('text', ''),
				'classes': el.get('classes', []),
				'style': el.get('style'),
			})
	return rows[:48]


def review_request_from_snapshot(
	snapshot: DesignSnapshot,
	*,
	user_task: str = '',
	scope: str = 'page',
	**kwargs: Any,
) -> ReviewRequest:
	return ReviewRequest(
		design_snapshot=snapshot,
		user_task=user_task,
		scope=scope,
		preview_url=snapshot.url,
		scan_id=snapshot.scan_id,
		**kwargs,
	)
