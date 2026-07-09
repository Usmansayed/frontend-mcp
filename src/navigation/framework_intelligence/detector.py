"""Framework detector — package.json, lockfiles, configs, folder structure."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import ProjectMetadata

_LOCKFILES: dict[str, str] = {
	'package-lock.json': 'npm',
	'pnpm-lock.yaml': 'pnpm',
	'yarn.lock': 'yarn',
	'bun.lockb': 'bun',
	'bun.lock': 'bun',
}

_CONFIG_CANDIDATES = (
	'vite.config.ts',
	'vite.config.js',
	'vite.config.mjs',
	'next.config.ts',
	'next.config.js',
	'next.config.mjs',
	'vue.config.js',
	'angular.json',
	'svelte.config.js',
	'svelte.config.ts',
	'astro.config.mjs',
	'astro.config.ts',
	'nuxt.config.ts',
	'nuxt.config.js',
	'webpack.config.js',
	'webpack.config.ts',
	'rsbuild.config.ts',
	'rsbuild.config.js',
	'tsconfig.json',
	'jsconfig.json',
	'turbo.json',
	'pnpm-workspace.yaml',
	'lerna.json',
)

_FRAMEWORK_DEPS: dict[str, str] = {
	'next': 'Next.js',
	'nuxt': 'Nuxt',
	'@angular/core': 'Angular',
	'@sveltejs/kit': 'SvelteKit',
	'svelte': 'Svelte',
	'astro': 'Astro',
	'vue': 'Vue',
	'react': 'React',
	'@remix-run/react': 'Remix',
	'solid-js': 'Solid',
	'@qwik.dev/core': 'Qwik',
}

_BUILD_TOOL_DEPS: dict[str, str] = {
	'vite': 'Vite',
	'webpack': 'Webpack',
	'@rsbuild/core': 'Rsbuild',
	'parcel': 'Parcel',
	'esbuild': 'esbuild',
	'rollup': 'Rollup',
}


def _read_json(path: Path) -> dict[str, Any]:
	try:
		return json.loads(path.read_text(encoding='utf-8'))
	except (OSError, json.JSONDecodeError):
		return {}


def _semver_major_minor(version: str | None) -> str | None:
	if not version:
		return None
	clean = version.strip().lstrip('^~>=<v')
	match = re.match(r'(\d+(?:\.\d+)?)', clean)
	return match.group(1) if match else clean


def _collect_deps(pkg: dict[str, Any]) -> dict[str, str]:
	out: dict[str, str] = {}
	for section in ('dependencies', 'devDependencies', 'peerDependencies'):
		raw = pkg.get(section) or {}
		if isinstance(raw, dict):
			for name, ver in raw.items():
				out[str(name)] = str(ver)
	return out


def _detect_package_manager(root: Path) -> str | None:
	for name, manager in _LOCKFILES.items():
		if (root / name).is_file():
			return manager
	return None


def _detect_language(root: Path, deps: dict[str, str]) -> str:
	if (root / 'tsconfig.json').is_file() or 'typescript' in deps:
		return 'typescript'
	return 'javascript'


def _detect_monorepo(root: Path, pkg: dict[str, Any]) -> bool:
	if pkg.get('workspaces'):
		return True
	for marker in ('pnpm-workspace.yaml', 'lerna.json', 'nx.json'):
		if (root / marker).is_file():
			return True
	turbo = root / 'turbo.json'
	if turbo.is_file():
		data = _read_json(turbo)
		if data.get('pipeline') or data.get('tasks'):
			return True
	packages_dir = root / 'packages'
	return packages_dir.is_dir() and any(packages_dir.iterdir())


def _detect_framework(deps: dict[str, str]) -> tuple[str | None, str | None, str | None]:
	priority = (
		'next',
		'nuxt',
		'@angular/core',
		'@sveltejs/kit',
		'astro',
		'@remix-run/react',
		'svelte',
		'vue',
		'react',
		'solid-js',
		'@qwik.dev/core',
	)
	for key in priority:
		if key not in deps:
			continue
		return _FRAMEWORK_DEPS[key], _semver_major_minor(deps[key]), key
	return None, None, None


def _detect_build_tool(deps: dict[str, str], root: Path, framework: str | None) -> str | None:
	if framework == 'Next.js':
		if (root / 'next.config.ts').is_file() or (root / 'next.config.js').is_file():
			return 'Turbopack/Webpack (Next.js)'
		return 'Next.js'
	for dep, label in _BUILD_TOOL_DEPS.items():
		if dep in deps:
			return label
	for pattern in ('vite.config.*', 'webpack.config.*', 'rsbuild.config.*'):
		if any(root.glob(pattern)):
			stem = pattern.split('.')[0].replace('*', '')
			return stem.replace('config', '').strip('.') or None
	return None


def _detect_rendering_and_router(root: Path, framework: str | None) -> tuple[str | None, str | None]:
	if framework == 'Next.js':
		has_app = (root / 'app').is_dir()
		has_pages = (root / 'pages').is_dir()
		router = 'app' if has_app else ('pages' if has_pages else None)
		mode = 'SSR/SSG (hybrid)'
		return mode, router
	if framework == 'Nuxt':
		return 'SSR/SSG (hybrid)', None
	if framework == 'Astro':
		return 'SSG/SSR (content-driven)', None
	if framework == 'Angular':
		return 'CSR/SSR (Angular Universal when configured)', None
	if framework == 'SvelteKit':
		return 'SSR/SSG (adapters)', None
	if (root / 'index.html').is_file() and (root / 'src').is_dir():
		return 'CSR', None
	return None, None


def _project_structure(root: Path) -> dict[str, Any]:
	def has(path: str) -> bool:
		return (root / path).exists()

	return {
		'has_src': has('src'),
		'has_app_dir': has('app'),
		'has_pages_dir': has('pages'),
		'has_public': has('public'),
		'has_components': has('src/components') or has('components'),
		'has_routes': has('src/routes') or has('src/router.jsx') or has('src/router.tsx'),
	}


def detect_project(repo_root: Path) -> ProjectMetadata:
	root = repo_root.resolve()
	degraded: list[str] = []
	pkg_path = root / 'package.json'
	if not pkg_path.is_file():
		return ProjectMetadata(
			repo_root=str(root),
			degraded=['package_json_missing'],
		)

	pkg = _read_json(pkg_path)
	deps = _collect_deps(pkg)
	framework, version, primary_package = _detect_framework(deps)
	package_manager = _detect_package_manager(root)
	language = _detect_language(root, deps)
	is_monorepo = _detect_monorepo(root, pkg)
	build_tool = _detect_build_tool(deps, root, framework)
	rendering_mode, router_mode = _detect_rendering_and_router(root, framework)
	config_files = [name for name in _CONFIG_CANDIDATES if (root / name).is_file()]

	if not framework:
		degraded.append('framework_unknown')

	return ProjectMetadata(
		repo_root=str(root),
		framework=framework,
		framework_version=version,
		build_tool=build_tool,
		package_manager=package_manager,
		language=language,
		is_monorepo=is_monorepo,
		rendering_mode=rendering_mode,
		router_mode=router_mode,
		config_files=config_files,
		project_structure=_project_structure(root),
		primary_package=primary_package,
		degraded=degraded,
	)
