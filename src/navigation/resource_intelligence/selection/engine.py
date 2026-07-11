"""Selection Intelligence — choose best asset with confidence and reasoning."""
from __future__ import annotations

from navigation.resource_intelligence.import_verification.icons import verify_icon_import
from navigation.resource_intelligence.models import ResourceAssetRef, ResourceCategory, ResourceDiscoveryRequest, ResourceSelection
from navigation.resource_intelligence.selection.context import SelectionContext


async def apply_context_scores(
	assets: list[ResourceAssetRef],
	ctx: SelectionContext,
	request: ResourceDiscoveryRequest,
) -> list[ResourceAssetRef]:
	for asset in assets:
		boost = 0.0
		reasons: list[str] = []
		if ctx.icon_family_hint:
			fam = asset.metadata.get('icon_family') or ''
			if fam == ctx.icon_family_hint:
				boost += 0.35
				reasons.append(f'framework_family_match:{fam}')
			elif asset.provider_id == ctx.icon_family_hint:
				boost += 0.3
				reasons.append(f'provider_family_match:{asset.provider_id}')
		for style in ctx.design_sense_styles:
			if style in ' '.join(asset.tags + asset.style).lower():
				boost += 0.08
				reasons.append(f'design_sense:{style}')
		if ctx.framework and ctx.framework.lower() in asset.provider_id.lower():
			boost += 0.1
		asset.score = min(1.0, asset.score + boost)
		if reasons:
			asset.metadata['selection_reasons'] = reasons
	return sorted(assets, key=lambda a: a.score, reverse=True)


async def select_best(
	assets: list[ResourceAssetRef],
	ctx: SelectionContext,
	request: ResourceDiscoveryRequest,
	*,
	icon_family: str | None = None,
) -> ResourceSelection | None:
	if not assets:
		return None
	ranked = await apply_context_scores(assets, ctx, request)
	best = ranked[0]
	alts = [a.resource_id for a in ranked[1:4]]
	reasoning = list(ctx.reasoning)
	reasoning.extend(best.metadata.get('selection_reasons') or [])
	verified_import = ''
	install_command = ''
	if best.category == ResourceCategory.ICON:
		fam = icon_family or best.metadata.get('icon_family') or ctx.icon_family_hint or 'lucide'
		icon_name = str(best.metadata.get('icon_name') or best.title).lower()
		icon_name = icon_name.replace(' ', '-')
		v = await verify_icon_import(fam, icon_name)
		if v.get('verified') == 'true':
			verified_import = v.get('verified_import', '')
			install_command = v.get('install_command', '')
			best.metadata['verified_import'] = verified_import
			best.metadata['install_command'] = install_command
			best.metadata['import_verified'] = True
		else:
			best.metadata['import_verified'] = False
			reasoning.append(f"import_unverified:{v.get('reason', '')}")
	confidence = min(1.0, best.score)
	if best.metadata.get('family_match'):
		confidence = min(1.0, confidence + 0.1)
	return ResourceSelection(
		chosen_resource_id=best.resource_id,
		provider_id=best.provider_id,
		category=best.category.value,
		confidence=round(confidence, 3),
		icon_family=icon_family or best.metadata.get('icon_family'),
		alternatives=alts,
		reasoning=reasoning,
		verified_import=verified_import,
		install_command=install_command,
	)
