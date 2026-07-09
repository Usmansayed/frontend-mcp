from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def artifact_dir(phase: str, root: Path | None = None) -> Path:
    base = root or Path.cwd() / "artifacts" / phase
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    d = base / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
