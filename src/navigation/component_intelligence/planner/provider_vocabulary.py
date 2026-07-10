"""Provider- and registry-specific search vocabulary."""

from __future__ import annotations

# Registry namespace -> preferred item naming vocabulary.
REGISTRY_VOCABULARY: dict[str, tuple[str, ...]] = {
	'@shadcn': ('navigation-menu', 'menubar', 'navbar', 'header', 'breadcrumb'),
	'@aceternity': ('navbar', 'navigation', 'header', 'floating-navbar', 'menu'),
	'@tailark': ('header', 'navbar', 'navigation', 'hero'),
	'@magicui': ('navbar', 'navigation', 'header', 'animated'),
	'@kokonutui': ('navbar', 'header', 'navigation'),
	'@cult-ui': ('navbar', 'header', 'navigation'),
	'@kibo-ui': ('navbar', 'header', 'navigation'),
	'@diceui': ('navbar', 'header', 'navigation'),
	'@motion-primitives': ('navigation', 'navbar', 'animated'),
	'@blocks': ('navbar', 'header', 'section', 'block'),
	'@shadcn-space': ('navbar', 'header', 'block'),
	'@pureui': ('navbar', 'header', 'navigation'),
	'@abui': ('navbar', 'header', 'navigation'),
	'@doras-ui': ('navbar', 'header', 'navigation'),
	'@8bitcn': ('navbar', 'header', 'navigation'),
	'@ai-elements': ('navbar', 'header', 'navigation'),
}

# External provider vocabulary (Group B — for future adapters).
EXTERNAL_PROVIDER_VOCABULARY: dict[str, tuple[str, ...]] = {
	'mui': ('app bar', 'toolbar', 'navigation', 'drawer'),
	'chakra_ui': ('menu', 'header', 'navbar', 'navigation'),
	'mantine': ('header', 'navbar', 'app shell', 'navigation'),
	'flowbite': ('navbar', 'header', 'navigation'),
	'heroui': ('navbar', 'header', 'navigation'),
	'park_ui': ('header', 'navigation'),
	'tremor': ('navbar', 'header', 'dashboard'),
	'melt_ui': ('menubar', 'navigation'),
	'web_awesome': ('navigation', 'header'),
	'react_aria': ('navigation', 'menu', 'toolbar'),
}

# Style / intent -> registries likely to have matching blocks.
STYLE_REGISTRY_AFFINITY: dict[str, tuple[str, ...]] = {
	'glassmorphism': ('@magicui', '@aceternity', '@kokonutui', '@cult-ui'),
	'glass': ('@magicui', '@aceternity', '@kokonutui'),
	'animated': ('@magicui', '@aceternity', '@motion-primitives'),
	'minimal': ('@shadcn', '@pureui', '@tailark', '@abui'),
	'modern': ('@tailark', '@shadcn', '@magicui', '@blocks'),
	'dashboard': ('@tailark', '@blocks', '@shadcn-space', '@tremor'),
	'enterprise': ('@shadcn', '@tailark', '@blocks'),
	'saas': ('@tailark', '@blocks', '@magicui', '@shadcn'),
	'premium': ('@aceternity', '@magicui', '@kokonutui'),
	'pricing': ('@tailark', '@blocks', '@shadcn', '@magicui'),
	'navbar': ('@aceternity', '@tailark', '@shadcn', '@magicui', '@kokonutui'),
	'header': ('@tailark', '@shadcn', '@blocks', '@aceternity'),
}

DEFAULT_REGISTRIES: tuple[str, ...] = (
	'@shadcn',
	'@aceternity',
	'@tailark',
	'@magicui',
	'@kokonutui',
	'@blocks',
	'@motion-primitives',
)


def registry_search_terms(registry: str, plan_terms: list[str]) -> list[str]:
	"""Pick plan terms relevant to a registry's vocabulary."""
	vocab = {v.lower() for v in REGISTRY_VOCABULARY.get(registry, ())}
	if not vocab:
		return plan_terms
	matched = [t for t in plan_terms if any(v in t.lower() or t.lower() in v for v in vocab)]
	if matched:
		return matched
	# Fall back to registry-native terms combined with component type from plan.
	native = list(REGISTRY_VOCABULARY.get(registry, ()))
	return native[:4] if native else plan_terms[:3]
