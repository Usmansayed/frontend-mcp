"""Health doctor — env/runtime checks with copy-paste fix commands."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


def _check(
	*,
	id: str,
	ok: bool,
	severity: str,
	detail: str,
	fix: str | None = None,
) -> dict[str, Any]:
	row: dict[str, Any] = {
		"id": id,
		"ok": bool(ok),
		"severity": severity,
		"detail": detail,
	}
	if fix:
		row["fix"] = fix
	return row


def build_health_doctor(
	*,
	url: str,
	reachable: bool,
	status: int | None,
	error: str | None,
	browser_runtime_available: bool,
	browser_manager: dict[str, Any] | None = None,
	package_version: str | None = None,
	version_skew: bool = False,
	restart_required: bool = False,
	restart_hint: str | None = None,
	repo_root_arg: str | None = None,
) -> dict[str, Any]:
	"""Deterministic doctor report for perception_health."""
	checks: list[dict[str, Any]] = []
	fixes: list[str] = []

	# 1) App URL
	if reachable:
		checks.append(
			_check(
				id="app_url",
				ok=True,
				severity="critical",
				detail=f"reachable {url} (status={status})",
			)
		)
	else:
		fix = (
			f"Start the app, then re-run: perception_health({{url: '{url}', intent: '<task>'}})"
		)
		checks.append(
			_check(
				id="app_url",
				ok=False,
				severity="critical",
				detail=error or f"unreachable {url} (status={status})",
				fix=fix,
			)
		)
		fixes.append(fix)

	# 2) browser-use
	if browser_runtime_available:
		checks.append(
			_check(
				id="browser_use",
				ok=True,
				severity="critical",
				detail="browser_use importable",
			)
		)
	else:
		fix = "pip install browser-use  # or: pip install -e \".[browser]\""
		checks.append(
			_check(
				id="browser_use",
				ok=False,
				severity="critical",
				detail="browser_use not importable — browser tools will fail",
				fix=fix,
			)
		)
		fixes.append(fix)

	# 3) Chromium / playwright binary hint
	chromium_ok = False
	chromium_detail = "no chromium binary found on PATH"
	for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
		path = shutil.which(name)
		if path:
			chromium_ok = True
			chromium_detail = f"found {name} at {path}"
			break
	# Playwright browsers often live under local app data — soft pass if browser_use ok
	if not chromium_ok and browser_runtime_available:
		chromium_ok = True
		chromium_detail = (
			"no PATH chrome; browser_use may still manage Chromium "
			"(run: playwright install chromium if sessions fail)"
		)
	if chromium_ok:
		checks.append(
			_check(
				id="chromium",
				ok=True,
				severity="warning",
				detail=chromium_detail,
			)
		)
	else:
		fix = "playwright install chromium"
		checks.append(
			_check(
				id="chromium",
				ok=False,
				severity="warning",
				detail=chromium_detail,
				fix=fix,
			)
		)
		fixes.append(fix)

	# 4) Node (Lighthouse audits)
	node = shutil.which("node")
	if node:
		checks.append(
			_check(
				id="node",
				ok=True,
				severity="warning",
				detail=f"node at {node}",
			)
		)
	else:
		fix = "Install Node.js 18+ and ensure `node` is on PATH (needed for Lighthouse audits)"
		checks.append(
			_check(
				id="node",
				ok=False,
				severity="warning",
				detail="node not on PATH — audit_* / full_diagnosis may degrade",
				fix=fix,
			)
		)
		fixes.append(fix)

	# 5) Repo root
	env_root = (
		str(repo_root_arg or "").strip()
		or str(os.environ.get("FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT") or "").strip()
		or str(os.environ.get("PERCEPTION_REPO_ROOT") or "").strip()
	)
	if env_root and Path(env_root).is_dir():
		checks.append(
			_check(
				id="repo_root",
				ok=True,
				severity="warning",
				detail=f"repo_root ok: {env_root}",
			)
		)
	elif env_root:
		fix = (
			f"Fix path or unset: FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT={env_root} "
			"(pass repo_root on session_start / resolve_* )"
		)
		checks.append(
			_check(
				id="repo_root",
				ok=False,
				severity="warning",
				detail=f"repo_root set but not a directory: {env_root}",
				fix=fix,
			)
		)
		fixes.append(fix)
	else:
		fix = (
			"Set FRONTEND_PERCEPTION_DEFAULT_REPO_ROOT to the app repo "
			"(or pass repo_root= on session_start / resolve_* / design tools)"
		)
		checks.append(
			_check(
				id="repo_root",
				ok=False,
				severity="info",
				detail="no default repo_root — resolvers/design graph need an explicit path",
				fix=fix,
			)
		)
		# info only — don't push into top fixes unless nothing else

	# 6) Version skew / restart
	if restart_required or version_skew:
		fix = restart_hint or (
			"Reload MCP / restart Cursor agent after pip install -e . --upgrade"
		)
		checks.append(
			_check(
				id="version_skew",
				ok=False,
				severity="critical",
				detail=f"package={package_version} skew/restart required",
				fix=fix,
			)
		)
		fixes.append(fix)
	else:
		checks.append(
			_check(
				id="version_skew",
				ok=True,
				severity="info",
				detail=f"package={package_version or 'unknown'}",
			)
		)

	# 7) Browser manager snapshot
	bm = browser_manager if isinstance(browser_manager, dict) else {}
	checks.append(
		_check(
			id="browser_manager",
			ok=True,
			severity="info",
			detail=(
				f"sessions={bm.get('active_sessions')} "
				f"running={bm.get('browser_running')} "
				f"restarts={bm.get('restart_count')}"
			),
		)
	)

	critical_fail = [c for c in checks if not c["ok"] and c["severity"] == "critical"]
	warning_fail = [c for c in checks if not c["ok"] and c["severity"] == "warning"]
	ok = len(critical_fail) == 0
	summary = (
		"doctor ok"
		if ok and not warning_fail
		else (
			f"doctor CRITICAL fail: {', '.join(c['id'] for c in critical_fail)}"
			if critical_fail
			else f"doctor warnings: {', '.join(c['id'] for c in warning_fail)}"
		)
	)

	# Prefer critical fixes first; cap list
	ordered_fixes: list[str] = []
	for c in checks:
		if not c["ok"] and c.get("fix") and c["severity"] == "critical":
			ordered_fixes.append(str(c["fix"]))
	for c in checks:
		if not c["ok"] and c.get("fix") and c["severity"] != "critical":
			fx = str(c["fix"])
			if fx not in ordered_fixes:
				ordered_fixes.append(fx)

	return {
		"ok": ok,
		"summary": summary,
		"checks": checks,
		"fix_commands": ordered_fixes[:8],
		"primary_browser": "perception",
		"note": (
			"Primary browser owner = Frontend Perception MCP. "
			"Do not parallel Cursor browser / Playwright MCP on the same app session."
		),
	}
