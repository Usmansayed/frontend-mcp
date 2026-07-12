"""Resolve bundled docs and default paths for installed vs dev checkout."""
from __future__ import annotations

import os
from pathlib import Path

from navigation.core.env import find_project_root


def navigation_root() -> Path:
    """Root of the ``navigation`` Python package."""
    return Path(__file__).resolve().parents[1]


def module_doc(*parts: str) -> Path:
    """Path to a markdown file under ``navigation/<module>/docs/``."""
    return navigation_root().joinpath(*parts)


def agent_guide_path() -> Path:
    """AGENT_GUIDE bundled with the MCP package."""
    return navigation_root() / "mcp" / "AGENT_GUIDE.md"


def validation_form_eval_path() -> Path:
    """Validation-form eval scenario doc bundled with MCP."""
    return navigation_root() / "mcp" / "evals" / "VALIDATION_FORM_EVAL.md"


def default_code_repo_root() -> Path:
    """
    Default ``repo_root`` for code-context tools.

    Uses FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT, else dev sandbox when present,
    else the process working directory (never assumes a monorepo checkout).
    """
    explicit = os.environ.get("FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    start = navigation_root()
    root = find_project_root(start)
    if root is not None:
        sandbox = root / "sandbox"
        if sandbox.is_dir():
            return sandbox

    return Path.cwd().resolve()
