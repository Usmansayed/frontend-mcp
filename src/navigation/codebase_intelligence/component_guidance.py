"""Codebase Intelligence guidance for component selection."""
from __future__ import annotations

import json
from pathlib import Path

from navigation.component_intelligence.integration_models import CodebaseGuidance
from navigation.component_intelligence.models import ComponentCandidate, ParsedQuery


def evaluate_component(
	candidate: ComponentCandidate,
	*,
	repo_root: Path,
	parsed_query: ParsedQuery | None = None,
) -> CodebaseGuidance:
	_ = parsed_query
	libraries: dict[str, str] = {}
	patterns: list[str] = []
	utilities: list[str] = []
	preferred: list[str] = []
	duplicates: list[str] = []
	degraded = ['codebase_guidance_heuristic']

	pkg = repo_root / 'package.json'
	if pkg.is_file():
		try:
			data = json.loads(pkg.read_text(encoding='utf-8'))
			deps = {**(data.get('dependencies') or {}), **(data.get('devDependencies') or {})}
			for key in ('react', 'next', '@radix-ui/react-slot', 'lucide-react', 'framer-motion', 'tailwindcss'):
				if key in deps:
					libraries[key] = str(deps[key])
		except (json.JSONDecodeError, OSError):
			degraded.append('package_json_unreadable')

	if (repo_root / 'components.json').is_file():
		patterns.append('shadcn_components_json')
		preferred.append('use_existing_shadcn_components_json_paths')
	if 'lucide-react' in libraries:
		utilities.append('lucide-react icons')
		preferred.append('prefer_lucide_icons_in_adapted_component')
	if (repo_root / 'lib' / 'utils.ts').is_file() or (repo_root / 'src' / 'lib' / 'utils.ts').is_file():
		utilities.append('cn() utility')
		patterns.append('lib/utils')

	components_dir = repo_root / 'components'
	if components_dir.is_dir():
		existing = [p.stem for p in components_dir.rglob('*.tsx')]
		if candidate.name in existing:
			duplicates.append(f'component_name_exists:{candidate.name}')

	return CodebaseGuidance(
		existing_patterns=patterns,
		reusable_utilities=utilities,
		existing_libraries=libraries,
		preferred_implementations=preferred,
		duplicate_risks=duplicates,
		degraded=degraded,
	)
