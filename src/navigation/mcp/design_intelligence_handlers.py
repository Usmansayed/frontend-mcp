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
		rec = await store.ensure(session_id)
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

	from navigation.engineering_knowledge import compile_live_spec, compile_reference_spec
	from navigation.engineering_knowledge.reference_binding import (
		bind_reference_spec,
		evaluate_revision_gate,
		get_reference_spec,
		resolve_psm_for_session,
	)

	session_id = str(
		arguments.get('session_id') or (snap_rec.session_id if snap_rec else '') or ''
	)
	bind_as_reference = bool(arguments.get('bind_as_reference', False))
	role = str(arguments.get('role') or ('reference' if bind_as_reference else 'current')).lower()
	psm = resolve_psm_for_session(session_id or None)

	if role in ('reference', 'bind'):
		eng_spec = compile_reference_spec(
			snapshot,
			provenance={'bound_as': 'reference', 'url': snapshot.url},
		)
		spec_dict = eng_spec.to_dict()
		bind_meta = bind_reference_spec(
			eng_spec,
			session_id=session_id or None,
			psm=psm,
			source='design_snapshot_reference',
			note='Bound from perception_build_design_snapshot(bind_as_reference/role=reference)',
		)
		if psm is not None:
			try:
				from navigation.coordination_intelligence.integration.bridge import get_coordinator_bridge

				get_coordinator_bridge().service.runtime.save(psm)
			except Exception:
				pass
		gate = evaluate_revision_gate(eng_spec, eng_spec, phase='reference_captured')
		unresolved = list(spec_dict.get('unresolved_by_impact') or [])
		return make_envelope(
			'perception_build_design_snapshot',
			ok=True,
			session_id=session_id or None,
			scan_id=snap_rec.scan_id if snap_rec else snapshot.scan_id,
			url=snapshot.url,
			data={
				'snapshot_id': snap_rec.snapshot_id if snap_rec else '',
				'scan_id': snap_rec.scan_id if snap_rec else snapshot.scan_id,
				'snapshot_summary': _snapshot_summary(snapshot),
				'snapshot': snapshot.to_dict(),
				'engineering_spec': spec_dict,
				'reference_engineering_spec': spec_dict,
				'spec_role': 'reference',
				'reference_bind': bind_meta,
				'spec_revision_gate': gate,
				'agent_summary': {
					'engineering_spec_coverage': spec_dict.get('coverage'),
					'unresolved_engineering_decisions': unresolved[:8],
					'spec_revision_gate': gate,
					'coordinator_headline': gate.get('host_action'),
					'advisory': [
						'Reference Spec bound. Implement from Spec, then remeasure (bind_as_reference=false) for SpecDiff gate.',
					],
				},
			},
			degraded=list(snapshot.degraded),
		)

	if psm is not None:
		psm.artifacts.snapshot_id = snap_rec.snapshot_id if snap_rec else psm.artifacts.snapshot_id
		try:
			from navigation.coordination_intelligence.planning.section_checklist import (
				seed_section_checklist_from_regions,
			)

			regions = list((snapshot.layout.regions if snapshot.layout else None) or [])
			checklist = seed_section_checklist_from_regions(psm, regions)
		except Exception:
			checklist = None
		try:
			from navigation.coordination_intelligence.integration.bridge import get_coordinator_bridge

			get_coordinator_bridge().service.runtime.save(psm)
		except Exception:
			pass
	else:
		checklist = None

	# Current (post-draft) Spec + SpecDiff vs bound reference
	eng_spec = compile_live_spec(snapshot)
	spec_dict = eng_spec.to_dict()
	ref_spec, ref_meta = get_reference_spec(
		session_id=session_id or None,
		psm=psm,
		reference_spec=arguments.get('reference_engineering_spec')
		if isinstance(arguments.get('reference_engineering_spec'), dict)
		else None,
	)
	gate = evaluate_revision_gate(eng_spec, ref_spec, phase='current')
	if ref_meta:
		gate['reference_meta'] = ref_meta
	unresolved = list(spec_dict.get('unresolved_by_impact') or [])
	headline = gate.get('host_action')
	if not ref_spec and unresolved:
		headline = unresolved[0].get('why') or headline

	return make_envelope(
		'perception_build_design_snapshot',
		ok=True,
		session_id=session_id or None,
		scan_id=snap_rec.scan_id if snap_rec else snapshot.scan_id,
		url=snapshot.url,
		data={
			'snapshot_id': snap_rec.snapshot_id if snap_rec else '',
			'scan_id': snap_rec.scan_id if snap_rec else snapshot.scan_id,
			'snapshot_summary': _snapshot_summary(snapshot),
			'snapshot': snapshot.to_dict(),
			'engineering_spec': spec_dict,
			'spec_role': 'current',
			'spec_revision_gate': gate,
			'engineering_delta': gate.get('engineering_delta'),
			'section_checklist': checklist,
			'agent_summary': {
				'engineering_spec_coverage': spec_dict.get('coverage'),
				'unresolved_engineering_decisions': unresolved[:8],
				'spec_revision_gate': gate,
				'revision_required': gate.get('revision_required'),
				'coordinator_headline': headline,
				'section_checklist': checklist,
				'advisory': [
					'Closed loop: if revision_required, fix drifts listed in spec_revision_gate then remeasure.',
					'After draft: observe+verify each section_checklist item before Ship Council / claim-done.',
				],
			},
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

	from navigation.engineering_knowledge import (
		compile_from_snapshot_dict,
		compile_live_spec,
		diff_specs,
	)
	from navigation.engineering_knowledge.reference_binding import (
		evaluate_revision_gate,
		get_reference_spec,
		resolve_psm_for_session,
	)

	session_id = str(
		arguments.get('session_id') or (snap_rec.session_id if snap_rec else '') or ''
	)
	psm = resolve_psm_for_session(session_id or None)
	if psm is None:
		from navigation.coordination_intelligence.models import ProjectSituationModel
		psm = ProjectSituationModel()
	current_spec = compile_live_spec(snapshot)
	engineering_delta = None
	reference_spec_summary = None
	ref_source = None

	# Prefer bound episode/session reference Spec over design-reference-registry
	bound_ref, bound_meta = get_reference_spec(
		session_id=session_id or None,
		psm=psm,
		reference_spec=arguments.get('reference_engineering_spec')
		if isinstance(arguments.get('reference_engineering_spec'), dict)
		else None,
	)
	if bound_ref is not None:
		engineering_delta = diff_specs(bound_ref, current_spec).to_dict()
		ref_source = bound_meta.get('source') or 'bound'
		reference_spec_summary = {
			'source': ref_source,
			'meta': bound_meta,
			'coverage': bound_ref.to_dict().get('coverage'),
			'top_resolved': [
				d.to_dict()
				for d in sorted(
					(x for x in bound_ref.decisions.values() if x.status == 'resolved'),
					key=lambda d: -d.impact_weight,
				)[:8]
			],
		}
	elif compare_references:
		try:
			from navigation.design_reference_registry.seeds import default_reference_registry

			reg = default_reference_registry()
			similar = reg.find_similar(snapshot, limit=1, user_task=user_task)
			if similar:
				best = similar[0]
				entry = reg.get(best.reference_id)
				if entry and entry.snapshot:
					ref_spec = compile_from_snapshot_dict(
						entry.snapshot,
						source_kind='reference',
						provenance={
							'reference_id': entry.id,
							'reference_name': entry.name,
							'source_url': entry.source_url,
						},
					)
					engineering_delta = diff_specs(ref_spec, current_spec).to_dict()
					ref_source = 'registry'
					reference_spec_summary = {
						'reference_id': entry.id,
						'reference_name': entry.name,
						'source': 'registry',
						'coverage': ref_spec.to_dict().get('coverage'),
						'top_resolved': [
							d.to_dict()
							for d in sorted(
								(x for x in ref_spec.decisions.values() if x.status == 'resolved'),
								key=lambda d: -d.impact_weight,
							)[:8]
						],
					}
		except Exception:
			engineering_delta = None

	revision_gate = evaluate_revision_gate(current_spec, bound_ref, phase='current')
	if bound_meta:
		revision_gate['reference_meta'] = bound_meta

	request = review_request_from_snapshot(
		snapshot,
		user_task=user_task,
		scope=str(arguments.get('scope') or 'page'),
	)
	report = await DesignSenseService().review(request, compare_references=compare_references)

	blocking = [f for f in report.findings if f.severity == 'blocking']
	spec_dict = current_spec.to_dict()
	delta_top = list((engineering_delta or {}).get('top_by_impact') or [])
	# Prefer SpecDiff engineering actions when available
	spec_actions = [
		{
			'decision_id': d.get('decision_id'),
			'kind': d.get('kind'),
			'severity': d.get('severity'),
			'impact_weight': d.get('impact_weight'),
			'detail': d.get('detail'),
			'from': d.get('from_value'),
			'to': d.get('to_value'),
		}
		for d in delta_top[:10]
	]
	gate_blocks = list(revision_gate.get('blocking_drifts') or [])
	headline = (
		revision_gate.get('host_action')
		if revision_gate.get('reference_bound')
		else (
			(delta_top[0].get('detail') if delta_top else None)
			or (spec_dict.get('unresolved_by_impact') or [{}])[0].get('why')
			or report.summary
		)
	)

	mode = str(arguments.get('mode') or 'review').strip().lower()
	if mode not in ('review', 'ship'):
		mode = 'review'
	explicit_ship = str(arguments.get('mode') or '').strip().lower() == 'ship'
	if mode == 'review' and not arguments.get('mode'):
		from navigation.coordination_intelligence.planning.engineering_strategy import (
			compile_engineering_strategy,
		)
		from navigation.coordination_intelligence.planning.ship_council import (
			should_recommend_ship_mode,
		)
		from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts

		bundle = load_runtime_artifacts()
		strategy_dict = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
		if should_recommend_ship_mode(psm, strategy_dict):
			mode = 'ship'

	if mode == 'ship':
		from navigation.coordination_intelligence.planning.engineering_strategy import (
			compile_engineering_strategy,
		)
		from navigation.coordination_intelligence.planning.ship_council import build_ship_council
		from navigation.coordination_intelligence.artifacts.loader import load_runtime_artifacts

		bundle = load_runtime_artifacts()
		strategy_dict = compile_engineering_strategy(psm, bundle.situation_policy_catalog).to_dict()
		# Explicit mode=ship must run detectors even when strategy is still minimal/hotfix.
		if explicit_ship:
			strategy_dict = {
				**strategy_dict,
				'influence_level': (
					strategy_dict.get('influence_level')
					if strategy_dict.get('influence_level') in ('structural', 'balanced')
					else 'balanced'
				),
				'task_scope': (
					strategy_dict.get('task_scope')
					if strategy_dict.get('task_scope') not in ('hotfix', 'surgical', 'debug')
					else 'design_driven'
				),
			}
		raw_dispositions = arguments.get('dispositions')
		dispositions = list(raw_dispositions) if isinstance(raw_dispositions, list) else []
		ship = build_ship_council(
			psm=psm,
			strategy=strategy_dict,
			snapshot=snapshot,
			engineering_delta=engineering_delta,
			revision_gate=revision_gate,
			findings=report.findings,
			dispositions=dispositions,
			force=explicit_ship,
		)
		ship_gate = ship.get('ship_gate') or {}
		council_clear = bool(ship_gate.get('council_clear'))
		challenges = list(ship.get('challenges') or [])
		coverage = str(ship_gate.get('coverage') or 'partial')
		coordination_evidence = {
			'capability_id': 'design_review',
			'outcome': 'success' if council_clear else 'degraded',
			'status': 'succeeded' if council_clear else 'provisional',
			'advancement_eligible': council_clear,
			'quality': {
				'mode': 'ship',
				'challenges_emitted': len(challenges),
				'open_high_roi': ship_gate.get('open_high_roi', 0),
				'council_clear': council_clear,
				'coverage': coverage,
			},
			'artifact_refs': {'snapshot_id': snap_rec.snapshot_id if snap_rec else ''},
		}
		ship_headline = (
			f"Ship Council: {len(challenges)} challenge(s); "
			f"gate={ship_gate.get('state')}; council_clear={council_clear}; "
			f"coverage={coverage}"
		)
		if council_clear and coverage in ('thin', 'partial'):
			next_hint = (
				'Council cleared with limited detector coverage. '
				'Before claim-done on structural work, snapshot a denser product surface '
				'(dashboard/settings shell) or accept low-confidence clear.'
			)
			advisory = [
				'ship_gate.council_clear is true but coverage is not full — '
				'do not treat empty challenges as strong design approval.',
			]
		elif council_clear:
			next_hint = (
				'Ship Council clear with adequate coverage; claim-done only if '
				'data.verified=true and section_checklist is complete when required.'
			)
			advisory = [
				'Ship Council clear. Confirm data.verified=true and section checklist '
				'before claiming done.',
			]
		else:
			next_hint = (
				'Revise high-ROI challenges, accept with engineering rationale, '
				'or ask_user for brand decisions.'
			)
			advisory = [
				'Ship Council challenges are decision-centric; do not claim done while ship_gate.council_clear is false.',
			]
		return make_envelope(
			'perception_design_review',
			ok=True,
			session_id=session_id or None,
			scan_id=snap_rec.scan_id if snap_rec else snapshot.scan_id,
			url=snapshot.url,
			data={
				'mode': 'ship',
				'snapshot_id': snap_rec.snapshot_id if snap_rec else '',
				'engineering_spec': spec_dict,
				'engineering_delta': engineering_delta,
				'spec_revision_gate': revision_gate,
				'framing': ship.get('framing'),
				'challenges': challenges,
				'ranked_roi': ship.get('ranked_roi'),
				'ship_gate': ship_gate,
				'ship_summary': ship.get('ship_summary'),
				'decision_ledger': ship.get('decision_ledger'),
				'rejected_dispositions': ship.get('rejected_dispositions'),
				'skipped_reason': ship.get('skipped_reason'),
				'passed': council_clear,
				'summary': ship_headline,
				'finding_count': len(challenges),
				'coordination_evidence': coordination_evidence,
				'agent_summary': {
					'mode': 'ship',
					'ship_gate': ship_gate,
					'ship_summary': ship.get('ship_summary'),
					'ship_council_hint': {
						'resource': 'perception://ship-council',
						'next': next_hint,
						'coverage': coverage,
					},
					'coordinator_headline': ship_headline,
					'spec_revision_gate': revision_gate,
					'advisory': advisory,
				},
			},
			degraded=list(report.degraded),
		)

	return make_envelope(
		'perception_design_review',
		ok=True,
		session_id=session_id or None,
		scan_id=snap_rec.scan_id if snap_rec else snapshot.scan_id,
		url=snapshot.url,
		data={
			'snapshot_id': snap_rec.snapshot_id if snap_rec else '',
			'engineering_spec': spec_dict,
			'engineering_delta': engineering_delta,
			'reference_engineering_spec': reference_spec_summary,
			'spec_revision_gate': revision_gate,
			'reference_source': ref_source,
			'passed': (
				report.passed
				and not revision_gate.get('revision_required')
				and not any(
					i.get('severity') == 'blocking'
					for i in ((engineering_delta or {}).get('items') or [])
				)
			),
			'summary': report.summary,
			'finding_count': len(report.findings),
			'blocking_count': len(blocking) + len(gate_blocks),
			'blocking_findings': [f.to_dict() for f in blocking[:10]],
			'top_findings': [f.to_dict() for f in report.findings[:12]],
			'prioritized_recommendations': (
				spec_actions
				or (report.consensus.prioritized_recommendations if report.consensus else [])
			),
			'consensus_removed_duplicates': (
				report.consensus.removed_duplicates if report.consensus else 0
			),
			'reference_comparisons': report.reference_comparisons,
			'consulted_reviewers': report.consulted_reviewers,
			'consulted_providers': report.consulted_providers,
			'report': report.to_dict(),
			'agent_summary': {
				'engineering_delta_top': delta_top[:8],
				'unresolved_engineering_decisions': spec_dict.get('unresolved_by_impact', [])[:8],
				'spec_revision_gate': revision_gate,
				'revision_required': revision_gate.get('revision_required'),
				'coordinator_headline': headline,
				'advisory': [
					'Prefer engineering_delta (SpecDiff) over English findings for rebuild decisions.',
				],
			},
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

