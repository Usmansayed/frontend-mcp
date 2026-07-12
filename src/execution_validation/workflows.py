"""Load EVW workflow definitions."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def validation_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "execution_layer" / "validation"


@lru_cache(maxsize=1)
def load_workflows() -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML required for execution validation")
    path = validation_dir() / "workflows.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def workflow_by_id(workflow_id: str) -> dict[str, Any] | None:
    for wf in load_workflows().get("workflows", []):
        if wf.get("workflow_id") == workflow_id:
            return wf
    return None


def all_workflow_ids() -> list[str]:
    return [w["workflow_id"] for w in load_workflows().get("workflows", []) if w.get("workflow_id")]
