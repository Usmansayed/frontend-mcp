"""Rehydrate ComponentCandidate from id — durable integrate without re-search."""
from __future__ import annotations

from .models import ComponentCandidate

# Filled by SearchExecutor / search handlers so integrate(candidate_id) keeps metadata.
_CANDIDATE_CACHE: dict[str, ComponentCandidate] = {}


def remember_candidates(candidates: list[ComponentCandidate]) -> None:
	for c in candidates:
		if c and c.id:
			_CANDIDATE_CACHE[c.id] = c
			# Also index bare name / registry:name forms.
			if c.registry and c.name:
				_CANDIDATE_CACHE[f"{c.registry.lstrip('@')}:{c.name}"] = c
				_CANDIDATE_CACHE[f"{c.registry}/{c.name}"] = c


def resolve_candidate_by_id(candidate_id: str) -> ComponentCandidate:
	"""Resolve a full candidate; never return an empty stub when cache/registry know it."""
	cid = str(candidate_id or "").strip()
	if not cid:
		return _thin_stub("")

	cached = _CANDIDATE_CACHE.get(cid)
	if cached is not None:
		return cached

	# provider:registry:name  OR  registry:name  OR  name
	parts = cid.split(":")
	if len(parts) >= 3:
		provider, registry, name = parts[0], parts[1], parts[-1]
	elif len(parts) == 2:
		provider, registry, name = "shadcn_ecosystem", parts[0], parts[1]
	else:
		provider, registry, name = "shadcn_ecosystem", "shadcn", parts[0]

	registry_ns = registry if registry.startswith("@") else f"@{registry}"
	# Prefer cache under alternate keys
	for key in (
		f"{provider}:{registry.lstrip('@')}:{name}",
		f"{provider}:{registry_ns.lstrip('@')}:{name}",
		f"{registry_ns}:{name}",
		f"{registry.lstrip('@')}:{name}",
		name,
	):
		hit = _CANDIDATE_CACHE.get(key)
		if hit is not None:
			return hit

	install_arg = f"{registry_ns}/{name}" if registry_ns.startswith("@") else name
	return ComponentCandidate(
		id=f"{provider}:{registry_ns.lstrip('@')}:{name}",
		provider=provider,
		provider_group="shadcn_ecosystem" if "shadcn" in provider or registry_ns == "@shadcn" else provider,
		name=name,
		title=name.replace("-", " ").title(),
		category="component",
		description=f"Rehydrated candidate {registry_ns}/{name}",
		registry=registry_ns,
		item_type="registry:ui",
		install_method=f"npx shadcn@latest add {install_arg}",
		framework="react",
		relevance_score=0.5,
		metadata={
			"rehydrated": True,
			"add_command_argument": install_arg,
			"matched_query": "candidate_id",
		},
	)


def _thin_stub(candidate_id: str) -> ComponentCandidate:
	parts = candidate_id.split(":")
	name = parts[-1] if parts else candidate_id
	provider = parts[0] if len(parts) > 1 else "unknown"
	return ComponentCandidate(
		id=candidate_id or "unknown",
		provider=provider,
		provider_group=provider,
		name=name,
		title=name,
		category="component",
		description="",
		framework="react",
	)
