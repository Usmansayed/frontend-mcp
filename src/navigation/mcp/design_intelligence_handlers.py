"""MCP handlers for design snapshot + design sense + consistency pipeline."""
from __future__ import annotations

from typing import Any

from navigation.consistency_intelligence.service import ConsistencyIntelligenceService, _project_id_from_url
from navigation.core.envelope import make_envelope
from navigation.core.scan_registry import ScanRegistry
from navigation.core.snapshot_registry import SnapshotRecord, SnapshotRegistry
from navigation.design_sense_intelligence import DesignSenseService
from navigation.design_sense_intelligence.snapshot_access import review_request_from_snapshot
from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.design_snapshot_engine.integrations.designlang import augment_snapshot_from_designlang
from navigation.design_snapshot_engine.models import DesignSnapshot
from navigation.visual_browser_intelligence.browser.session_store import SessionStore


async def _build_or_load_snapshot(
	store: SessionStore,
	scans: ScanRegistry,
	snapshots: SnapshotRegistry,
	arguments: dict[str, Any],
) -> tuple[DesignSnapshot | None, SnapshotRecord | None, dict[str, Any] | None]:
	snapshot_id = str(arguments.get('snapshot_id') or '').strip()
	scan_id = str(arguments.get('scan_id') or '').strip()
	session_id = str(arguments.get('session_id') or '').strip()
	use_designlang = bool(arguments.get('use_designlang', False))

	if snapshot_id:
		rec = snapshots.get(snapshot_id)
		if rec is None:
			return None, None, make_envelope('', ok=False, error=f'unknown snapshot_id: {snapshot_id}')
		return DesignSnapshot.from_dict(rec.snapshot), rec, None

	if scan_id:
		existing = snapshots.get_by_scan(scan_id)
		if existing:
			return DesignSnapshot.from_dict(existing.snapshot), existing, None
		scan_rec = scans.get(scan_id)
		if scan_rec is None:
			return None, None, make_envelope('', ok=False, error=f'unknown scan_id: {scan_id}')
		session_id = scan_rec.session_id

	if not session_id:
		return None, None, make_envelope('', ok=False, error='session_id, scan_id, or snapshot_id required')

	try:
		rec = store.require(session_id)
	except KeyError as exc:
		return None, None, make_envelope('', ok=False, error=str(exc))

	engine = DesignSnapshotEngine()
	obs_dict: dict[str, Any] = {}
	if scan_id:
		scan_rec = scans.get(scan_id)
		if scan_rec:
			obs_dict = scan_rec.observation or {}

	snapshot = await engine.capture_from_session(
		rec.browser,
		visual_insights=obs_dict.get('visual_insights'),
		a11y_tree=obs_dict.get('a11y_tree', ''),
		dom_text=obs_dict.get('dom_text', ''),
		screenshot_ref=obs_dict.get('screenshot_path'),
		scan_id=scan_id or None,
	)

	if use_designlang and snapshot.url:
		snapshot = augment_snapshot_from_designlang(snapshot, snapshot.url)

	snap_rec = snapshots.register(
		snapshot=snapshot.to_dict(),
		url=snapshot.url,
		scan_id=scan_id or None,
		session_id=session_id,
	)
	return snapshot, snap_rec, None


def _snapshot_summary(snapshot: DesignSnapshot) -> dict[str, Any]:
	return {
		'url': snapshot.url,
		'typography_families': snapshot.typography.font_families[:6],
		'font_sizes': snapshot.typography.font_sizes_px[:8],
		'palette_size': len(snapshot.colors.palette),
		'wcag_failures': len(snapshot.colors.wcag_failures),
		'contrast_matrix_size': len(snapshot.colors.contrast_matrix),
		'spacing_off_scale': snapshot.spacing.off_scale_count,
		'layout_tree_nodes': len(snapshot.layout.layout_tree),
		'layout_issues': len(snapshot.layout.issues),
		'interactive_count': snapshot.components.interactive_count,
		'token_count': len(snapshot.design_tokens.css_variables),
		'degraded': list(snapshot.degraded),
	}


async def handle_build_design_snapshot(
	store: SessionStore,
	scans: ScanRegistry,
	snapshots: SnapshotRegistry,
	arguments: dict[str, Any],
) -> dict[str, Any]:
	snapshot, snap_rec, err = await _build_or_load_snapshot(store, scans, snapshots, arguments)
	if err:
		return {**err, 'tool': 'perception_build_design_snapshot'}

	return make_envelope(
		'perception_build_design_snapshot',
		ok=True,
		session_id=str(arguments.get('session_id') or (snap_rec.session_id if snap_rec else '')),
		scan_id=snap_rec.scan_id if snap_rec else snapshot.scan_id,
		url=snapshot.url,
		data={
			'snapshot_id': snap_rec.snapshot_id if snap_rec else '',
			'scan_id': snap_rec.scan_id if snap_rec else snapshot.scan_id,
			'snapshot_summary': _snapshot_summary(snapshot),
			'snapshot': snapshot.to_dict(),
		},
		degraded=list(snapshot.degraded),
	)


async def handle_design_review(
	store: SessionStore,
	scans: ScanRegistry,
	snapshots: SnapshotRegistry,
	arguments: dict[str, Any],
) -> dict[str, Any]:
	user_task = str(arguments.get('user_task') or 'Review this page design')
	compare_references = bool(arguments.get('compare_references', True))

	snapshot, snap_rec, err = await _build_or_load_snapshot(store, scans, snapshots, arguments)
	if err:
		return {**err, 'tool': 'perception_design_review'}

	request = review_request_from_snapshot(
		snapshot,
		user_task=user_task,
		scope=str(arguments.get('scope') or 'page'),
	)
	report = await DesignSenseService().review(request, compare_references=compare_references)

	blocking = [f for f in report.findings if f.severity == 'blocking']
	return make_envelope(
		'perception_design_review',
		ok=True,
		session_id=str(arguments.get('session_id') or (snap_rec.session_id if snap_rec else '')),
		scan_id=snap_rec.scan_id if snap_rec else snapshot.scan_id,
		url=snapshot.url,
		data={
			'snapshot_id': snap_rec.snapshot_id if snap_rec else '',
			'passed': report.passed,
			'summary': report.summary,
			'finding_count': len(report.findings),
			'blocking_count': len(blocking),
			'blocking_findings': [f.to_dict() for f in blocking[:10]],
			'top_findings': [f.to_dict() for f in report.findings[:12]],
			'prioritized_recommendations': (
				report.consensus.prioritized_recommendations if report.consensus else []
			),
			'consensus_removed_duplicates': (
				report.consensus.removed_duplicates if report.consensus else 0
			),
			'reference_comparisons': report.reference_comparisons,
			'consulted_reviewers': report.consulted_reviewers,
			'consulted_providers': report.consulted_providers,
			'report': report.to_dict(),
		},
		degraded=list(report.degraded),
	)


async def handle_consistency_review(
	store: SessionStore,
	scans: ScanRegistry,
	snapshots: SnapshotRegistry,
	arguments: dict[str, Any],
) -> dict[str, Any]:
	"""Refresh graph from snapshot + run batch consistency audit."""
	snapshot, snap_rec, err = await _build_or_load_snapshot(store, scans, snapshots, arguments)
	if err:
		return {**err, 'tool': 'perception_consistency_review'}

	repo_root = arguments.get('repo_root')
	project_id = str(arguments.get('project_id') or _project_id_from_url(snapshot.url))
	service = ConsistencyIntelligenceService(repo_root=repo_root) if repo_root else ConsistencyIntelligenceService()

	await service.refresh_graph(
		project_id=project_id,
		design_snapshot=snapshot,
		scan_id=snap_rec.scan_id if snap_rec else snapshot.scan_id,
		repo_root=repo_root,
	)
	audit_detail = service.audit_snapshot_detail(snapshot, project_id=project_id)
	report = service.audit_snapshot(snapshot, project_id=project_id)

	return make_envelope(
		'perception_consistency_review',
		ok=True,
		url=snapshot.url,
		data={
			'passed': report.passed,
			'summary': report.summary,
			'findings': [f.to_dict() for f in report.findings],
			'grouped_findings': audit_detail.get('grouped_findings', []),
			'elements_audited': audit_detail.get('elements_audited', 0),
			'project_id': project_id,
			'report': report.to_dict(),
		},
		degraded=list(report.degraded),
	)


async def handle_consistency_audit(
	store: SessionStore,
	scans: ScanRegistry,
	snapshots: SnapshotRegistry,
	arguments: dict[str, Any],
) -> dict[str, Any]:
	"""Batch audit — assumes graph already refreshed."""
	snapshot, _snap_rec, err = await _build_or_load_snapshot(store, scans, snapshots, arguments)
	if err:
		return {**err, 'tool': 'perception_consistency_audit'}

	repo_root = arguments.get('repo_root')
	project_id = str(arguments.get('project_id') or _project_id_from_url(snapshot.url))
	service = ConsistencyIntelligenceService(repo_root=repo_root) if repo_root else ConsistencyIntelligenceService()
	audit_detail = service.audit_snapshot_detail(
		snapshot,
		project_id=project_id,
		max_elements=int(arguments.get('max_elements', 40)),
	)

	return make_envelope(
		'perception_consistency_audit',
		ok=True,
		url=snapshot.url,
		data=audit_detail,
		degraded=list(audit_detail.get('degraded') or []),
	)


async def handle_design_knowledge_query(
	_arguments: dict[str, Any],
) -> dict[str, Any]:
	query_id = str(_arguments.get('query_id') or '').strip()
	if not query_id:
		return make_envelope(
			'perception_design_knowledge_query',
			ok=False,
			error='query_id is required',
		)
	params = _arguments.get('params') or {}
	if not isinstance(params, dict):
		params = {}
	project_id = str(_arguments.get('project_id') or 'default')
	repo_root = _arguments.get('repo_root')

	service = ConsistencyIntelligenceService(repo_root=repo_root) if repo_root else ConsistencyIntelligenceService()
	resp = service.query(query_id, params, project_id=project_id)

	return make_envelope(
		'perception_design_knowledge_query',
		ok=True,
		data={'knowledge': resp.to_dict(), 'summary': resp.summary_text()},
		degraded=list(resp.degraded),
	)


async def handle_design_graph_summary(
	arguments: dict[str, Any],
) -> dict[str, Any]:
	project_id = str(arguments.get('project_id') or 'default')
	repo_root = arguments.get('repo_root')

	service = ConsistencyIntelligenceService(repo_root=repo_root) if repo_root else ConsistencyIntelligenceService()
	resp = service.graph_summary(project_id=project_id)

	return make_envelope(
		'perception_design_graph_summary',
		ok=True,
		data={'knowledge': resp.to_dict(), 'summary': resp.summary_text()},
		degraded=list(resp.degraded),
	)


async def handle_consistency_assess(
	arguments: dict[str, Any],
) -> dict[str, Any]:
	selector = str(arguments.get('selector') or '').strip()
	actual = arguments.get('actual') or arguments.get('actual_values') or {}
	if not selector:
		return make_envelope('perception_consistency_assess', ok=False, error='selector is required')
	if not isinstance(actual, dict) or not actual:
		return make_envelope('perception_consistency_assess', ok=False, error='actual object required')

	project_id = str(arguments.get('project_id') or 'default')
	repo_root = arguments.get('repo_root')
	service = ConsistencyIntelligenceService(repo_root=repo_root) if repo_root else ConsistencyIntelligenceService()
	report = service.assess_consistency(
		selector=selector,
		actual={str(k): str(v) for k, v in actual.items()},
		context=arguments.get('context'),
		properties=arguments.get('properties'),
		project_id=project_id,
	)
	assess, explain = service.validator.assess_with_explanation(
		selector=selector,
		actual={str(k): str(v) for k, v in actual.items()},
		context=arguments.get('context'),
		properties=arguments.get('properties'),
		project_id=project_id,
	)

	return make_envelope(
		'perception_consistency_assess',
		ok=True,
		data={
			'passed': report.passed,
			'summary': report.summary,
			'findings': [f.to_dict() for f in report.findings],
			'assess': assess.to_dict(),
			'explain': explain.to_dict() if explain else None,
			'report': report.to_dict(),
		},
		degraded=list(report.degraded),
	)


async def handle_consistency_propose_fix(
	arguments: dict[str, Any],
) -> dict[str, Any]:
	standard_id = str(arguments.get('standard_id') or '').strip()
	if not standard_id:
		return make_envelope('perception_consistency_propose_fix', ok=False, error='standard_id is required')

	project_id = str(arguments.get('project_id') or 'default')
	repo_root = arguments.get('repo_root')
	service = ConsistencyIntelligenceService(repo_root=repo_root) if repo_root else ConsistencyIntelligenceService()
	resp = service.propose_fix(
		standard_id=standard_id,
		selector=str(arguments.get('selector') or ''),
		actual=arguments.get('actual'),
		project_id=project_id,
	)

	return make_envelope(
		'perception_consistency_propose_fix',
		ok=True,
		data={
			'knowledge': resp.to_dict(),
			'summary': resp.recommendation.detail if resp.recommendation else '',
		},
		degraded=list(resp.degraded),
	)


async def handle_design_graph_refresh(
	store: SessionStore,
	scans: ScanRegistry,
	snapshots: SnapshotRegistry,
	arguments: dict[str, Any],
) -> dict[str, Any]:
	"""Run Discovery Pipeline — ingest knowledge from enabled sources into the graph."""
	repo_root = arguments.get('repo_root')
	project_id = str(arguments.get('project_id') or 'default')
	enabled_raw = arguments.get('enabled_sources')
	enabled_sources: frozenset[str] | None = None
	if isinstance(enabled_raw, list) and enabled_raw:
		enabled_sources = frozenset(str(s) for s in enabled_raw)

	snapshot: DesignSnapshot | None = None
	if arguments.get('design_snapshot'):
		snapshot = DesignSnapshot.from_dict(arguments['design_snapshot'])
	elif arguments.get('snapshot_id') or arguments.get('scan_id') or arguments.get('session_id'):
		snapshot, _snap_rec, err = await _build_or_load_snapshot(store, scans, snapshots, arguments)
		if err:
			return {**err, 'tool': 'perception_design_graph_refresh'}

	if snapshot is None and enabled_sources is None:
		if repo_root:
			enabled_sources = frozenset({'codebase', 'tokens'})
		else:
			return make_envelope(
				'perception_design_graph_refresh',
				ok=False,
				error='repo_root or snapshot (session_id/scan_id/snapshot_id/design_snapshot) required',
			)

	if snapshot and snapshot.url and project_id == 'default':
		project_id = _project_id_from_url(snapshot.url)

	service = ConsistencyIntelligenceService(repo_root=repo_root) if repo_root else ConsistencyIntelligenceService()
	graph, degraded, stats = await service.refresh_graph(
		project_id=project_id,
		design_snapshot=snapshot,
		scan_id=str(arguments.get('scan_id') or '') or None,
		enabled_sources=enabled_sources,
		repo_root=repo_root,
	)
	summary = service.graph_summary(project_id=project_id)

	return make_envelope(
		'perception_design_graph_refresh',
		ok=True,
		url=snapshot.url if snapshot else '',
		data={
			'project_id': project_id,
			'graph_version': graph.meta.graph_version,
			'snapshot_count': graph.meta.snapshot_count,
			'merge_stats': stats.to_dict(),
			'knowledge': summary.to_dict(),
			'summary': summary.summary_text(),
		},
		degraded=degraded,
	)

