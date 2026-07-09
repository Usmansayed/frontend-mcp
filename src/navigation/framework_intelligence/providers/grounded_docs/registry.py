"""Grounded Docs library registry — adapter-only routing (not in detector)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GroundedDocsLibrarySpec:
	"""Maps a detected npm package to Grounded Docs library + on-demand scrape source."""

	library: str
	default_source_url: str
	display_name: str


# Keys are npm package names as detected from package.json (not framework marketing names).
LIBRARY_SPECS: dict[str, GroundedDocsLibrarySpec] = {
	'react': GroundedDocsLibrarySpec('react', 'https://react.dev/reference/react', 'React'),
	'react-dom': GroundedDocsLibrarySpec('react', 'https://react.dev/reference/react', 'React'),
	'next': GroundedDocsLibrarySpec('nextjs', 'https://nextjs.org/docs', 'Next.js'),
	'vue': GroundedDocsLibrarySpec('vue', 'https://vuejs.org/guide/introduction.html', 'Vue'),
	'nuxt': GroundedDocsLibrarySpec('nuxt', 'https://nuxt.com/docs', 'Nuxt'),
	'@angular/core': GroundedDocsLibrarySpec('angular', 'https://angular.dev/overview', 'Angular'),
	'svelte': GroundedDocsLibrarySpec('svelte', 'https://svelte.dev/docs/svelte/overview', 'Svelte'),
	'@sveltejs/kit': GroundedDocsLibrarySpec('sveltekit', 'https://kit.svelte.dev/docs', 'SvelteKit'),
	'astro': GroundedDocsLibrarySpec('astro', 'https://docs.astro.build/en/getting-started/', 'Astro'),
	'@remix-run/react': GroundedDocsLibrarySpec('remix', 'https://remix.run/docs/en/main', 'Remix'),
	'solid-js': GroundedDocsLibrarySpec('solid', 'https://www.solidjs.com/docs/latest', 'Solid'),
}


def resolve_library_spec(primary_package: str | None, framework: str | None) -> GroundedDocsLibrarySpec | None:
	if primary_package and primary_package in LIBRARY_SPECS:
		return LIBRARY_SPECS[primary_package]
	if framework:
		needle = framework.lower().replace('.', '')
		for spec in LIBRARY_SPECS.values():
			if needle in spec.display_name.lower().replace('.', '').replace(' ', ''):
				return spec
	return None
