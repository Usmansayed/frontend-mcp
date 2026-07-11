"""Resolve active icon family for a project or request."""
from __future__ import annotations

import json
import os
from pathlib import Path

from navigation.resource_intelligence.graph.icon_families import ICON_FAMILIES, IconFamily, get_icon_family
from navigation.resource_intelligence.models import ResourceDiscoveryRequest

_FAMILY_CACHE = Path(os.environ.get('RESOURCE_ICON_FAMILY_CACHE', '.cache/resource_icon_family.json'))

_NPM_TO_FAMILY: dict[str, str] = {
	'lucide-react': 'lucide',
	'@heroicons/react': 'heroicons',
	'@tabler/icons-react': 'tabler-icons',
	'@phosphor-icons/react': 'phosphor-icons',
	'@remixicon/react': 'remix-icon',
}


def detect_family_from_package_json(root: Path | None = None) -> str | None:
	root = root or Path.cwd()
	pkg_path = root / 'package.json'
	if not pkg_path.is_file():
		return None
	try:
		pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
	except json.JSONDecodeError:
		return None
	deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
	for npm_pkg, family_id in _NPM_TO_FAMILY.items():
		if npm_pkg in deps:
			return family_id
	return None


def load_persisted_family() -> str | None:
	if not _FAMILY_CACHE.is_file():
		return None
	try:
		data = json.loads(_FAMILY_CACHE.read_text(encoding='utf-8'))
		fid = str(data.get('icon_family') or '').strip()
		return fid if fid and get_icon_family(fid) else None
	except json.JSONDecodeError:
		return None


def persist_icon_family(family_id: str) -> None:
	_FAMILY_CACHE.parent.mkdir(parents=True, exist_ok=True)
	_FAMILY_CACHE.write_text(
		json.dumps({'icon_family': family_id}, indent=2),
		encoding='utf-8',
	)


def resolve_icon_family(
	request: ResourceDiscoveryRequest,
	*,
	project_root: Path | None = None,
) -> IconFamily | None:
	if request.icon_family:
		return get_icon_family(request.icon_family)
	env_family = os.environ.get('RESOURCE_ICON_FAMILY', '').strip()
	if env_family:
		return get_icon_family(env_family)
	persisted = load_persisted_family()
	if persisted:
		return get_icon_family(persisted)
	detected = detect_family_from_package_json(project_root)
	if detected:
		return get_icon_family(detected)
	return get_icon_family('lucide')
