"""Stable Framework Intelligence contract for Component Intelligence."""
from __future__ import annotations

from pathlib import Path

from navigation.component_intelligence.integration_models import (
	DocumentationBundle,
	FixPlan,
	FrameworkGuidance,
	FoundationSelection,
)
from navigation.component_intelligence.models import ComponentCandidate

from .component_guidance import evaluate_component
from .service import FrameworkIntelligenceService

MODULE_NAME = 'framework_intelligence'


class FrameworkIntelligenceAdapter:
	"""Public contract surface — implementation may evolve behind this API."""

	module_name = MODULE_NAME

	async def evaluate_component(
		self,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
	) -> FrameworkGuidance:
		return await evaluate_component(candidate, repo_root=repo_root)

	async def fetch_install_documentation(
		self,
		candidate: ComponentCandidate,
		*,
		repo_root: Path,
		selection: FoundationSelection | None = None,
	) -> DocumentationBundle:
		degraded: list[str] = []
		steps: list[str] = []
		required_deps: list[str] = []
		peer_deps: list[str] = []
		citations: list[str] = []
		config: list[str] = []
		provider_notes: list[str] = []
		common_issues: list[str] = []

		if candidate.install_method:
			steps.append(candidate.install_method)
		if candidate.source:
			citations.append(candidate.source)

		meta_deps = candidate.metadata.get('registry_dependencies') or []
		if isinstance(meta_deps, list):
			peer_deps.extend(str(d) for d in meta_deps)
			required_deps.extend(str(d) for d in meta_deps)

		if selection:
			config.extend(selection.guidance.framework.required_configuration)
			provider_notes.extend(selection.guidance.framework.compatibility_warnings)
			for warning in selection.guidance.framework.compatibility_warnings:
				if 'missing' in warning:
					common_issues.append(warning)

		topic = f'install {candidate.name} {candidate.category or "component"}'
		try:
			svc = FrameworkIntelligenceService()
			docs = await svc.fetch_docs(repo_root, topic=topic)
			degraded.extend(docs.degraded)
			if docs.summary:
				provider_notes.append(docs.summary)
			if docs.citations:
				citations.extend(docs.citations)
			if docs.content:
				provider_notes.append(f'grounded_docs:{docs.provider}')
				for line in docs.content.splitlines():
					lower = line.lower().strip()
					if lower.startswith('npm ') or lower.startswith('pnpm ') or lower.startswith('yarn '):
						steps.append(line.strip())
					if 'peer' in lower and 'depend' in lower:
						common_issues.append(line.strip()[:200])
		except Exception as exc:
			degraded.append(f'grounded_docs_unavailable:{type(exc).__name__}')

		if not degraded:
			degraded.append('framework_documentation_heuristic')

		return DocumentationBundle(
			installation_steps=steps,
			required_dependencies=required_deps,
			peer_dependencies=peer_deps,
			required_configuration=config,
			tailwind_plugins=[],
			css_variables=[],
			fonts=[],
			icons=['lucide-react'] if 'lucide' in ' '.join(required_deps).lower() else [],
			common_issues=common_issues,
			breaking_changes=[],
			provider_notes=provider_notes,
			citations=list(dict.fromkeys(citations)),
			degraded=list(dict.fromkeys(degraded)),
		)

	async def plan_framework_repairs(
		self,
		issue: str,
		*,
		selection: FoundationSelection,
		documentation: DocumentationBundle | None,
		repo_root: Path,
	) -> FixPlan:
		_ = repo_root
		actions: list[str] = []
		doc_refs: list[str] = []

		if selection.guidance.framework.issues:
			actions.append('resolve_framework_issues:' + ';'.join(selection.guidance.framework.issues[:3]))
		if selection.guidance.framework.compatibility_warnings:
			actions.append('address_framework_warnings')
		for dep in selection.guidance.framework.required_dependencies[:3]:
			actions.append(f'verify_dependency:{dep}')

		if documentation:
			doc_refs.extend(documentation.citations)
			for step in documentation.installation_steps[:3]:
				actions.append(f'verify_install_step:{step}')
			actions.append('fetch_framework_docs_if_needed')

		if 'import' in issue.lower():
			actions.append('fix_import_paths_per_components_json')
		if 'hydration' in issue.lower():
			actions.append('add_use_client_or_split_server_component')

		return FixPlan(
			issue=issue,
			actions=actions or ['read_framework_docs_and_retry'],
			consulted_modules=[MODULE_NAME],
			documentation_refs=doc_refs,
			degraded=['framework_repair_heuristic'],
		)
