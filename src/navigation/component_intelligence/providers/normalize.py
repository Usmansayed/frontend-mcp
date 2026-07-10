"""Normalize raw provider payloads into ComponentCandidate."""
from __future__ import annotations

from typing import Any

from ..models import ComponentCandidate


def normalize_shadcn_item(
	item: dict[str, Any],
	*,
	provider: str,
	provider_group: str,
	registry: str,
	registry_homepage: str | None,
	item_url_template: str | None,
	relevance_score: float,
	matched_query: str | None = None,
	search_pass: int | None = None,
	plan_confidence: float | None = None,
) -> ComponentCandidate:
	name = str(item.get('name') or '').strip()
	title = str(item.get('title') or name).strip()
	description = str(item.get('description') or '').strip()
	item_type = str(item.get('type') or 'registry:ui')
	category = _category_from_type(item_type)
	tags = _tags_from_item(item)
	install_arg = f'{registry}/{name}' if registry.startswith('@') else name
	install_method = f'npx shadcn@latest add {install_arg}'
	source = _item_source_url(item_url_template, name, registry_homepage)
	component_id = f'{provider}:{registry.lstrip("@")}:{name}'

	return ComponentCandidate(
		id=component_id,
		provider=provider,
		provider_group=provider_group,
		name=name,
		title=title,
		category=category,
		description=description,
		tags=tags,
		preview=registry_homepage,
		install_method=install_method,
		framework='react',
		source=source,
		registry=registry,
		item_type=item_type,
		relevance_score=relevance_score,
		metadata={
			'add_command_argument': item.get('addCommandArgument'),
			'registry_dependencies': item.get('registryDependencies') or [],
			'matched_query': matched_query,
			'search_pass': search_pass,
			'plan_confidence': plan_confidence,
			'original_request': None,
		},
	)


def _category_from_type(item_type: str) -> str:
	if 'block' in item_type:
		return 'block'
	if 'page' in item_type:
		return 'page'
	if 'hook' in item_type:
		return 'hook'
	if 'theme' in item_type:
		return 'theme'
	if 'example' in item_type:
		return 'example'
	return 'component'


def _tags_from_item(item: dict[str, Any]) -> list[str]:
	tags: list[str] = []
	for key in ('categories', 'tags', 'keywords'):
		val = item.get(key)
		if isinstance(val, list):
			tags.extend(str(v) for v in val if v)
	item_type = item.get('type')
	if item_type:
		tags.append(str(item_type).replace('registry:', ''))
	return list(dict.fromkeys(tags))


def _item_source_url(template: str | None, name: str, homepage: str | None) -> str | None:
	if not template:
		return homepage
	if '{name}' not in template:
		return template
	url = template.replace('{name}.json', f'{name}.json').replace('{name}', name)
	if '{style}' in url:
		url = url.replace('{style}', 'new-york')
	return url
