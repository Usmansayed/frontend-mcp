"""Ecosystem adapters — Framework, Consistency, Design Sense hints for Resource Intelligence."""
from __future__ import annotations

import json
from pathlib import Path

from navigation.resource_intelligence.graph.icon_families import get_icon_family
from navigation.resource_intelligence.selection.context import SelectionContext


_FRAMEWORK_ICON_FAMILY: dict[str, str] = {
	'lucide-react': 'lucide',
	'@heroicons/react': 'heroicons',
	'@tabler/icons-react': 'tabler-icons',
	'@phosphor-icons/react': 'phosphor-icons',
	'@remixicon/react': 'remix-icon',
	'@mui/icons-material': 'material-symbols',
	'@mui/material': 'material-symbols',
}


async def gather_selection_context(
	*,
	repo_root: str = '',
	project_id: str = 'default',
	design_sense_profile: str | None = None,
) -> tuple[SelectionContext, list[str]]:
	degraded: list[str] = []
	ctx = SelectionContext(repo_root=repo_root, project_id=project_id)
	root = Path(repo_root) if repo_root else None

	if root and root.is_dir():
		try:
			from navigation.framework_intelligence import FrameworkIntelligenceService

			meta = FrameworkIntelligenceService().detect(root)
			ctx.framework = meta.framework or ''
			ctx.primary_package = meta.primary_package or ''
			try:
				pkg = json.loads((root / 'package.json').read_text(encoding='utf-8'))
				deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
				for dep, family in _FRAMEWORK_ICON_FAMILY.items():
					if dep in deps:
						ctx.icon_family_hint = family
						break
			except Exception:
				pass
		except Exception:
			degraded.append('framework_context_unavailable')

		try:
			from navigation.consistency_intelligence.service import ConsistencyIntelligenceService

			csvc = ConsistencyIntelligenceService(repo_root=str(root))
			summary_resp = csvc.graph_summary()
			ctx.pdg_summary = summary_resp.data if hasattr(summary_resp, 'data') else {}
			for qid in ('typography.scale', 'spacing.system', 'color.palette'):
				try:
					resp = csvc.query(qid, {})
					if hasattr(resp, 'data'):
						ctx.pdg_queries[qid] = resp.data
				except Exception:
					pass
		except Exception:
			degraded.append('consistency_context_unavailable')

	if design_sense_profile:
		ctx.design_sense_styles = [s.strip() for s in design_sense_profile.split(',') if s.strip()]
	elif ctx.pdg_summary:
		standards = str(ctx.pdg_summary).lower()
		for style in ('minimal', 'rounded', 'enterprise', 'playful', 'glass', 'brutalist', 'corporate'):
			if style in standards:
				ctx.design_sense_styles.append(style)

	if not ctx.icon_family_hint and root:
		from navigation.resource_intelligence.planning.icon_family import detect_family_from_package_json

		detected = detect_family_from_package_json(root)
		if detected:
			ctx.icon_family_hint = detected

	if ctx.icon_family_hint and get_icon_family(ctx.icon_family_hint):
		ctx.reasoning.append(f'framework_icon_family:{ctx.icon_family_hint}')

	return ctx, degraded
