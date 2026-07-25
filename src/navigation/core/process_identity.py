"""MCP process identity — detect in-memory registry wipe and stale process vs install."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

PROCESS_BOOT_ID = (
    str(os.environ.get("PERCEPTION_PROCESS_BOOT_ID") or "").strip()
    or f"boot_{uuid.uuid4().hex[:12]}"
)
PROCESS_STARTED_AT = time.time()


def process_identity_dict() -> dict[str, object]:
    return {
        "process_boot_id": PROCESS_BOOT_ID,
        "process_started_at": PROCESS_STARTED_AT,
        "process_uptime_s": round(time.time() - PROCESS_STARTED_AT, 1),
        # Host (Cursor) may restart the MCP stdio process without warning —
        # treat boot_id change as session wipe, not idle timeout.
        "session_durability_note": (
            "In-memory sessions die if process_boot_id changes. "
            "On unknown session_id: perception_health → session_start → observe."
        ),
    }


def _package_mtime() -> float | None:
    """Newest mtime among installed package roots (navigation + dist-info)."""
    candidates: list[Path] = []
    try:
        import navigation

        candidates.append(Path(navigation.__file__).resolve().parent)
    except Exception:
        pass
    try:
        from importlib.metadata import distribution

        dist = distribution("frontend-perception-engine")
        # Prefer RECORD / METADATA under dist-info
        for name in ("METADATA", "RECORD", "WHEEL"):
            try:
                candidates.append(Path(str(dist.locate_file(name))).resolve())
            except Exception:
                continue
    except Exception:
        pass
    mtimes: list[float] = []
    for path in candidates:
        try:
            if path.is_file():
                mtimes.append(path.stat().st_mtime)
            elif path.is_dir():
                # Sample a few high-churn modules that ship every fix batch.
                for rel in (
                    "core/code_revision.py",
                    "resource_intelligence/providers/fontsource/provider.py",
                    "execution_runtime/policies/timeout.py",
                ):
                    probe = path / rel
                    if probe.is_file():
                        mtimes.append(probe.stat().st_mtime)
                mtimes.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(mtimes) if mtimes else None


def version_skew_report(package_version: str | None) -> dict[str, Any]:
    """Detect disk package newer than this process, or CODE_REVISION mismatch."""
    from navigation.core.code_revision import CODE_REVISION

    pkg = str(package_version or "").strip() or None
    mtime = _package_mtime()
    reasons: list[str] = []

    if pkg and pkg != CODE_REVISION:
        reasons.append("code_revision_mismatch")
    # Package files written after this process started → install without restart.
    if mtime is not None and mtime > (PROCESS_STARTED_AT + 2.0):
        reasons.append("process_predates_package_install")

    skewed = bool(reasons)
    return {
        "version_skew": skewed,
        "version_skew_reasons": reasons,
        "code_revision": CODE_REVISION,
        "package_mtime": mtime,
        "restart_required": skewed,
        "restart_hint": (
            "Restart the Frontend MCP server (Cursor MCP restart). "
            "package_version alone is not proof the process loaded the new code — "
            "require a new process_boot_id and version_skew=false before trusting live tools."
            if skewed
            else None
        ),
    }


def session_lost_message(session_id: str | None = None) -> str:
    sid = str(session_id or "").strip()
    prefix = f"unknown session_id: {sid}" if sid else "unknown session_id"
    return (
        f"{prefix} — in-memory sessions were wiped "
        f"(MCP process restart is the usual cause; idle timeout does not remove session_ids). "
        f"Re-run perception_health → perception_session_start → observe. "
        f"process_boot_id={PROCESS_BOOT_ID}"
    )


def registry_lost_message(kind: str, value: str | None = None) -> str:
    label = f"{kind}: {value}" if value else kind
    return (
        f"unknown {label} — scan/snapshot registries are in-memory and die with MCP restart. "
        f"Re-bootstrap: session_start → navigate_and_observe → rebuild snapshot. "
        f"process_boot_id={PROCESS_BOOT_ID}"
    )
