"""Unit tests for framework detection and cache."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
	sys.path.insert(0, str(SRC))

from navigation.framework_intelligence.cache import FrameworkDocsCache
from navigation.framework_intelligence.detector import detect_project


def test_detect_sandbox_react_vite() -> None:
	meta = detect_project(ROOT / "sandbox")
	assert meta.framework == "React"
	assert meta.framework_version == "18.3"
	assert meta.primary_package == "react"
	assert meta.build_tool == "Vite"
	assert meta.package_manager == "npm"
	assert meta.language == "javascript"
	assert meta.rendering_mode == "CSR"
	assert "vite.config.js" in meta.config_files
	assert meta.project_structure.get("has_src") is True


def test_cache_invalidates_on_version_change() -> None:
	cache = FrameworkDocsCache()
	key = cache.make_key(framework="React", framework_version="18.3", topic="hooks")
	cache.set(key, version_key="React:18.3", value={"content": "a"})
	assert cache.get(key, version_key="React:18.3") is not None
	assert cache.get(key, version_key="React:19.0") is None


def main() -> int:
	test_detect_sandbox_react_vite()
	test_cache_invalidates_on_version_change()
	print("framework intelligence: PASS")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
