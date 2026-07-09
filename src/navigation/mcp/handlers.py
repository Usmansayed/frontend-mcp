"""MCP tool handlers — thin wrappers over navigation.perception engine."""
from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from navigation.perception.budget import OutputBudget, apply_observation_budget
from navigation.perception.dev_insights import collect_dev_insights_during
from navigation.perception.preflight import preflight_check, wait_for_page_ready
from navigation.perception.scan import scan_page
from navigation.perception.verification import SuccessCriteria, evaluate_js, verify

from .diff import diff_observations
from .envelope import agent_summary_from_observation, agent_summary_from_report, make_envelope
from .scan_registry import ScanRegistry
from .session_store import SessionStore
from .visual_response import attach_diff_visuals, attach_observation_visuals, visual_uris_for_scan


def _resolve_url(base: str, url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urljoin(base.rstrip("/") + "/", url.lstrip("/"))


def _criteria_from_dict(criteria_raw: dict[str, Any]) -> SuccessCriteria:
    return SuccessCriteria(
        url_contains=list(criteria_raw.get("url_contains") or []),
        url_not_contains=list(criteria_raw.get("url_not_contains") or []),
        url_regex=criteria_raw.get("url_regex"),
        text_contains=list(criteria_raw.get("text_contains") or []),
        text_absent=list(criteria_raw.get("text_absent") or []),
        js_assertions=list(criteria_raw.get("js_assertions") or []),
        accept_urls=list(criteria_raw.get("accept_urls") or []),
    )


def _budget_from_args(budget_raw: dict[str, Any] | None) -> OutputBudget:
    budget_raw = budget_raw or {}
    return OutputBudget(
        max_a11y_chars=int(budget_raw.get("max_a11y_chars", 4000)),
        max_dom_chars=int(budget_raw.get("max_dom_chars", 4000)),
        max_list_items=int(budget_raw.get("max_list_items", 30)),
    )


def _detail_mode(arguments: dict[str, Any]) -> str:
	detail = str(arguments.get('detail') or 'full').strip().lower()
	return detail if detail in {'full', 'summary_only'} else 'full'


def _screenshot_options(arguments: dict[str, Any]) -> tuple[bool, str, str | None, bool]:
	include = arguments.get('include_screenshot', True)
	if include is False:
		return False, 'viewport', None, True
	mode_raw = arguments.get('screenshot_mode')
	if mode_raw:
		mode = str(mode_raw).strip().lower()
	elif isinstance(include, str):
		mode = include.strip().lower()
	else:
		mode = 'viewport'
	if mode not in {'viewport', 'full', 'element'}:
		mode = 'viewport'
	selector = arguments.get('screenshot_selector')
	annotate = bool(arguments.get('annotate_screenshot', True))
	return True, mode, str(selector) if selector else None, annotate


def _visual_data_block(scan_id: str, obs_dict: dict[str, Any]) -> dict[str, Any]:
	return {
		'visual': {
			**visual_uris_for_scan(scan_id, obs_dict),
			'visual_insights': obs_dict.get('visual_insights'),
		},
	}


def _observation_payload(
	obs_dict: dict[str, Any],
	summary: dict[str, Any],
	detail: str,
	scan_id: str,
) -> dict[str, Any]:
	data: dict[str, Any] = {
		'agent_summary': summary,
		**_visual_data_block(scan_id, obs_dict),
	}
	if detail == 'full':
		data['observation'] = obs_dict
	return data


def _require_session(store: SessionStore, session_id: str) -> tuple[Any | None, dict[str, Any] | None]:
    if not session_id:
        return None, make_envelope("", ok=False, error="session_id required")
    try:
        return store.require(session_id), None
    except KeyError as exc:
        return None, make_envelope("", ok=False, error=str(exc))


async def handle_health(arguments: dict[str, Any]) -> dict[str, Any]:
    url = str(arguments.get("url") or "http://localhost:5173")
    reachable = False
    status: int | None = None
    error: str | None = None
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            status = resp.status
            reachable = status == 200
    except urllib.error.HTTPError as exc:
        status = exc.code
        reachable = exc.code < 500
        error = str(exc)
    except Exception as exc:
        error = str(exc)

    return make_envelope(
        "perception_health",
        ok=reachable,
        url=url,
        error=None if reachable else (error or f"unreachable (status={status})"),
        data={"reachable": reachable, "status": status},
    )


async def handle_session_start(
    store: SessionStore,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    base_url = str(arguments.get("base_url") or "http://localhost:5173")
    headless = bool(arguments.get("headless", True))
    viewport = arguments.get("viewport") or {}
    try:
        rec = await store.start(
            base_url=base_url,
            headless=headless,
            viewport_width=int(viewport.get("width", 1920)),
            viewport_height=int(viewport.get("height", 1080)),
        )
    except Exception as exc:
        return make_envelope("perception_session_start", ok=False, error=str(exc))

    return make_envelope(
        "perception_session_start",
        session_id=rec.session_id,
        run_id=rec.current_run_id,
        url=rec.base_url,
        data={
            "session_id": rec.session_id,
            "run_id": rec.current_run_id,
            "base_url": rec.base_url,
            "artifacts_dir": str(rec.artifacts_dir),
        },
    )


async def handle_session_end(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_session_end", ok=False, error="session_id required")
    ended = await store.end(session_id)
    return make_envelope(
        "perception_session_end",
        ok=ended,
        session_id=session_id,
        error=None if ended else f"unknown session_id: {session_id}",
        data={"ended": ended},
    )


async def handle_navigate_and_observe(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    url_arg = str(arguments.get("url") or "")
    if not session_id or not url_arg:
        return make_envelope(
            "perception_navigate_and_observe",
            ok=False,
            error="session_id and url required",
        )

    try:
        rec = store.require(session_id)
    except KeyError as exc:
        return make_envelope("perception_navigate_and_observe", ok=False, error=str(exc))

    target = _resolve_url(rec.base_url, url_arg)
    include_shot, shot_mode, shot_selector, annotate = _screenshot_options(arguments)
    detail = _detail_mode(arguments)
    budget_raw = arguments.get("budget") or {}
    budget = OutputBudget(
        max_a11y_chars=int(budget_raw.get("max_a11y_chars", 4000)),
        max_dom_chars=int(budget_raw.get("max_dom_chars", 4000)),
        max_list_items=int(budget_raw.get("max_list_items", 30)),
    )

    images_dir = rec.artifacts_dir / "images" if include_shot else None
    result = await scan_page(
        rec.browser,
        target,
        images_dir=images_dir,
        name=f"scan-{rec.run_counter}",
        budget=budget,
        screenshot_mode=shot_mode,
        screenshot_selector=shot_selector,
        annotate_screenshot=annotate,
        console_service=rec.console,
        network_service=rec.network,
        har_dir=rec.artifacts_dir / "network",
    )

    if not result.ok:
        return make_envelope(
            "perception_navigate_and_observe",
            ok=False,
            session_id=session_id,
            run_id=rec.current_run_id,
            url=target,
            error=result.error,
            degraded=result.degraded,
            data={"preflight": result.preflight.to_dict() if result.preflight else None},
        )

    obs_dict = result.observation.to_dict() if result.observation else {}
    scan_rec = scans.register(
        session_id=session_id,
        run_id=rec.current_run_id,
        url=result.url,
        observation=obs_dict,
    )
    summary = agent_summary_from_observation(obs_dict)

    return attach_observation_visuals(
        make_envelope(
            "perception_navigate_and_observe",
            session_id=session_id,
            run_id=rec.current_run_id,
            scan_id=scan_rec.scan_id,
            url=result.url,
            degraded=result.degraded,
            data={
                "scan_id": scan_rec.scan_id,
                **_observation_payload(obs_dict, summary, detail, scan_rec.scan_id),
                "detail": detail,
                "preflight": result.preflight.to_dict() if result.preflight else None,
            },
        ),
        obs_dict,
    )


async def handle_verify(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    criteria_raw = arguments.get("criteria") or {}
    if not session_id:
        return make_envelope("perception_verify", ok=False, error="session_id required")

    try:
        rec = store.require(session_id)
    except KeyError as exc:
        return make_envelope("perception_verify", ok=False, error=str(exc))

    criteria = _criteria_from_dict(criteria_raw)
    vr = await verify(rec.browser, criteria)

    data: dict[str, Any] = {
        "verified": vr.ok,
        "url": vr.url,
        "reasons": vr.reasons,
        "auto_merged": vr.auto_merged,
        "feedback": vr.feedback(),
    }
    scan_id: str | None = None
    envelope = make_envelope(
        "perception_verify",
        session_id=session_id,
        run_id=rec.current_run_id,
        url=vr.url,
        ok=True,
        data=data,
    )

    if not vr.ok:
        obs_dict, scan_rec = await _observe_and_register(
            rec,
            scans,
            session_id,
            include_screenshot=True,
            name=f"verify-fail-{rec.run_counter}",
            extra_visual_labels=[f"verify: {r}" for r in vr.reasons[:5]],
        )
        scan_id = scan_rec.scan_id
        summary = agent_summary_from_observation(obs_dict)
        data["failure_scan_id"] = scan_id
        data["agent_summary"] = summary
        data.update(_visual_data_block(scan_id, obs_dict))
        envelope["scan_id"] = scan_id
        envelope = attach_observation_visuals(envelope, obs_dict)

    return envelope


async def handle_execute_script(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    script = str(arguments.get("script") or "")
    if not session_id or not script:
        return make_envelope(
            "perception_execute_script",
            ok=False,
            error="session_id and script required",
        )

    try:
        rec = store.require(session_id)
    except KeyError as exc:
        return make_envelope("perception_execute_script", ok=False, error=str(exc))

    capture = bool(arguments.get("capture_insights_during", True))
    scan_before = scans.register(
        session_id=session_id,
        run_id=rec.current_run_id,
        url=await _current_url(rec.browser),
        observation={"phase": "before_execute"},
    )

    script_ok = False
    return_value: Any = None
    insights_dict: dict[str, Any] | None = None
    error: str | None = None

    async def _run() -> None:
        nonlocal return_value
        return_value = await evaluate_js(rec.browser, script)

    try:
        if capture:
            insights = await collect_dev_insights_during(rec.browser, _run)
            insights_dict = insights.to_dict()
        else:
            await _run()
        script_ok = True
    except Exception as exc:
        error = str(exc)

    await wait_for_page_ready(rec.browser, timeout=5.0)
    from navigation.perception.observation import collect_observation

    obs = await collect_observation(
        rec.browser,
        images_dir=rec.artifacts_dir / "images",
        name=f"after-exec-{rec.run_counter}",
        annotate_screenshot=True,
    )
    scan_after = scans.register(
        session_id=session_id,
        run_id=rec.current_run_id,
        url=obs.url,
        observation=obs.to_dict(),
    )

    return attach_observation_visuals(
        make_envelope(
            "perception_execute_script",
            ok=script_ok,
            session_id=session_id,
            run_id=rec.current_run_id,
            scan_id=scan_after.scan_id,
            url=obs.url,
            error=error,
            degraded=obs.degraded,
            data={
                "script_ok": script_ok,
                "return_value": return_value,
                "scan_id_before": scan_before.scan_id,
                "scan_id_after": scan_after.scan_id,
                "dev_insights": insights_dict,
                "agent_summary": agent_summary_from_observation(obs.to_dict()),
                **_visual_data_block(scan_after.scan_id, obs.to_dict()),
            },
        ),
        obs.to_dict(),
    )


async def _current_url(browser: Any) -> str:
    from navigation.perception.verification import read_current_url

    return await read_current_url(browser)


async def _observe_and_register(
    rec: Any,
    scans: ScanRegistry,
    session_id: str,
    *,
    include_screenshot: bool = True,
    budget: OutputBudget | None = None,
    name: str | None = None,
    screenshot_mode: str = "viewport",
    screenshot_selector: str | None = None,
    annotate_screenshot: bool = True,
    extra_visual_labels: list[str] | None = None,
) -> tuple[dict[str, Any], Any]:
    from navigation.perception.observation import collect_observation

    images_dir = rec.artifacts_dir / "images" if include_screenshot else None
    obs = await collect_observation(
        rec.browser,
        images_dir=images_dir,
        name=name or f"observe-{rec.run_counter}",
        screenshot_mode=screenshot_mode,  # type: ignore[arg-type]
        screenshot_selector=screenshot_selector,
        annotate_screenshot=annotate_screenshot,
        extra_visual_labels=extra_visual_labels,
        console_service=rec.console,
        network_service=rec.network,
        har_dir=rec.artifacts_dir / "network",
    )
    obs_dict = obs.to_dict()
    if budget:
        obs_dict = apply_observation_budget(obs_dict, budget)
    scan_rec = scans.register(
        session_id=session_id,
        run_id=rec.current_run_id,
        url=obs.url,
        observation=obs_dict,
    )
    return obs_dict, scan_rec


async def handle_navigate(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    url_arg = str(arguments.get("url") or "")
    if not session_id or not url_arg:
        return make_envelope("perception_navigate", ok=False, error="session_id and url required")

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_navigate"}

    target = _resolve_url(rec.base_url, url_arg)
    pf = await preflight_check(rec.browser, target)
    return make_envelope(
        "perception_navigate",
        ok=pf.ok,
        session_id=session_id,
        run_id=rec.current_run_id,
        url=pf.url or target,
        error=pf.error,
        degraded=pf.degraded,
        data={"preflight": pf.to_dict()},
    )


async def handle_observe(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_observe", ok=False, error="session_id required")

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_observe"}

    include_shot, shot_mode, shot_selector, annotate = _screenshot_options(arguments)
    detail = _detail_mode(arguments)
    budget = _budget_from_args(arguments.get("budget"))
    obs_dict, scan_rec = await _observe_and_register(
        rec,
        scans,
        session_id,
        include_screenshot=include_shot,
        budget=budget,
        screenshot_mode=shot_mode,
        screenshot_selector=shot_selector,
        annotate_screenshot=annotate,
    )
    summary = agent_summary_from_observation(obs_dict)
    return attach_observation_visuals(
        make_envelope(
            "perception_observe",
            session_id=session_id,
            run_id=rec.current_run_id,
            scan_id=scan_rec.scan_id,
            url=obs_dict.get("url") or "",
            degraded=list(obs_dict.get("degraded") or []),
            data={
                "scan_id": scan_rec.scan_id,
                **_observation_payload(obs_dict, summary, detail, scan_rec.scan_id),
                "detail": detail,
            },
        ),
        obs_dict,
    )


async def handle_execute_actions(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    from navigation.perception.scripted_actions import (
        click_button_text,
        click_link_text,
        set_input_by_label,
    )

    session_id = str(arguments.get("session_id") or "")
    actions = arguments.get("actions") or []
    if not session_id:
        return make_envelope("perception_execute_actions", ok=False, error="session_id required")
    if not isinstance(actions, list) or not actions:
        return make_envelope("perception_execute_actions", ok=False, error="actions list required")

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_execute_actions"}

    capture = bool(arguments.get("capture_insights_during", True))
    results: list[dict[str, Any]] = []
    insights_dict: dict[str, Any] | None = None
    all_ok = True
    error: str | None = None

    async def _run_actions() -> None:
        nonlocal all_ok, error
        for idx, action in enumerate(actions):
            if not isinstance(action, dict):
                all_ok = False
                results.append({"index": idx, "ok": False, "error": "action must be object"})
                error = "invalid action"
                break
            kind = str(action.get("type") or "")
            ok = False
            if kind == "click_button":
                ok = await click_button_text(rec.browser, str(action.get("text") or ""))
            elif kind == "click_link":
                ok = await click_link_text(rec.browser, str(action.get("text") or ""))
            elif kind == "set_input":
                ok = await set_input_by_label(
                    rec.browser,
                    str(action.get("label") or ""),
                    str(action.get("value") or ""),
                )
            else:
                results.append({"index": idx, "type": kind, "ok": False, "error": "unknown action type"})
                all_ok = False
                error = f"unknown action type: {kind}"
                break
            results.append({"index": idx, "type": kind, "ok": ok})
            if not ok:
                all_ok = False
                error = f"action {idx} ({kind}) failed"
                break
            await wait_for_page_ready(rec.browser, timeout=3.0)

    try:
        if capture:
            insights = await collect_dev_insights_during(rec.browser, _run_actions)
            insights_dict = insights.to_dict()
        else:
            await _run_actions()
    except Exception as exc:
        all_ok = False
        error = str(exc)

    obs_dict, scan_rec = await _observe_and_register(
        rec,
        scans,
        session_id,
        name=f"after-actions-{rec.run_counter}",
        annotate_screenshot=True,
    )
    return attach_observation_visuals(
        make_envelope(
            "perception_execute_actions",
            ok=all_ok,
            session_id=session_id,
            run_id=rec.current_run_id,
            scan_id=scan_rec.scan_id,
            url=obs_dict.get("url") or "",
            error=error,
            degraded=list(obs_dict.get("degraded") or []),
            data={
                "actions_ok": all_ok,
                "action_results": results,
                "scan_id": scan_rec.scan_id,
                "dev_insights": insights_dict,
                "agent_summary": agent_summary_from_observation(obs_dict),
                **_visual_data_block(scan_rec.scan_id, obs_dict),
            },
        ),
        obs_dict,
    )


async def handle_diff(scans: ScanRegistry, arguments: dict[str, Any]) -> dict[str, Any]:
    before_id = str(arguments.get("scan_id_before") or "")
    after_id = str(arguments.get("scan_id_after") or "")
    if not before_id or not after_id:
        return make_envelope(
            "perception_diff",
            ok=False,
            error="scan_id_before and scan_id_after required",
        )

    before_rec = scans.get(before_id)
    after_rec = scans.get(after_id)
    if before_rec is None or after_rec is None:
        missing = []
        if before_rec is None:
            missing.append(before_id)
        if after_rec is None:
            missing.append(after_id)
        return make_envelope(
            "perception_diff",
            ok=False,
            error=f"unknown scan_id(s): {', '.join(missing)}",
        )

    diff = diff_observations(
        before_rec.observation,
        after_rec.observation,
        artifacts_dir=Path(str(after_rec.observation.get("screenshot_path") or "")).parent.parent
        if after_rec.observation.get("screenshot_path")
        else None,
        scan_id_before=before_id,
        scan_id_after=after_id,
    )
    visual_diff = diff.get("visual_diff") or {}
    has_visual = bool(visual_diff.get("side_by_side_path") or visual_diff.get("heatmap_path"))
    return attach_diff_visuals(
        make_envelope(
            "perception_diff",
            ok=True,
            session_id=after_rec.session_id,
            data={
                "scan_id_before": before_id,
                "scan_id_after": after_id,
                "diff": diff,
                "has_changes": diff["url_changed"]
                or diff["dom_text_changed"]
                or bool(diff["new_blocking_issues"])
                or bool(diff.get("new_visual_blocking")),
                "has_visual_diff": has_visual,
            },
        ),
        visual_diff,
    )


async def handle_auth_gate(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.perception.auth_gate import check_auth_gate

    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_auth_gate", ok=False, error="session_id required")

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_auth_gate"}

    gate = await check_auth_gate(rec.browser)
    return make_envelope(
        "perception_auth_gate",
        ok=True,
        session_id=session_id,
        run_id=rec.current_run_id,
        url=gate.url,
        data={
            "requires_human": gate.requires_human,
            "reason": gate.reason,
            "gate": gate.to_dict(),
        },
    )


async def handle_probe_form(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.perception.form_probe import probe_validation_form

    session_id = str(arguments.get("session_id") or "")
    form = str(arguments.get("form") or "validation")
    if not session_id:
        return make_envelope("perception_probe_form", ok=False, error="session_id required")

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_probe_form"}

    if form != "validation":
        return make_envelope(
            "perception_probe_form",
            ok=False,
            session_id=session_id,
            error=f"unsupported form probe: {form}",
        )

    probe = await probe_validation_form(rec.browser, rec.base_url)
    return make_envelope(
        "perception_probe_form",
        ok=probe.ok,
        session_id=session_id,
        run_id=rec.current_run_id,
        url=probe.form_url,
        error=probe.error,
        data={"probe": probe.to_dict()},
    )


async def handle_probe_guards(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.perception.route_guards import probe_maze_guards, probe_route_guard

    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_probe_guards", ok=False, error="session_id required")

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_probe_guards"}

    mode = str(arguments.get("mode") or "maze")
    if mode == "maze":
        result = await probe_maze_guards(rec.browser, rec.base_url)
    elif mode == "routes":
        routes = arguments.get("routes") or []
        guards = []
        for spec in routes:
            if not isinstance(spec, dict):
                continue
            guard = await probe_route_guard(
                rec.browser,
                rec.base_url,
                str(spec.get("route") or "/"),
                expected_redirect=spec.get("expected_redirect"),
                requires_auth=bool(spec.get("requires_auth", False)),
                requires_role=spec.get("requires_role"),
            )
            guards.append(guard)
        from navigation.perception.route_guards import GuardProbeResult

        result = GuardProbeResult(ok=bool(guards), guards=guards)
    else:
        return make_envelope(
            "perception_probe_guards",
            ok=False,
            session_id=session_id,
            error=f"unsupported mode: {mode}",
        )

    return make_envelope(
        "perception_probe_guards",
        ok=result.ok,
        session_id=session_id,
        run_id=rec.current_run_id,
        error=result.error,
        data={"probe": result.to_dict()},
    )


async def handle_state_save(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    state_id = str(arguments.get("state_id") or "")
    if not session_id or not state_id:
        return make_envelope(
            "perception_state_save",
            ok=False,
            error="session_id and state_id required",
        )

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_state_save"}

    snap = await rec.state_manager.snapshot(rec.browser, state_id)
    return make_envelope(
        "perception_state_save",
        ok=True,
        session_id=session_id,
        run_id=rec.current_run_id,
        url=snap.url,
        data={"state": snap.to_dict()},
    )


async def handle_state_restore(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    state_id = str(arguments.get("state_id") or "")
    if not session_id or not state_id:
        return make_envelope(
            "perception_state_restore",
            ok=False,
            error="session_id and state_id required",
        )

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_state_restore"}

    restored = await rec.state_manager.restore(rec.browser, state_id)
    url = await _current_url(rec.browser) if restored else ""
    return make_envelope(
        "perception_state_restore",
        ok=restored,
        session_id=session_id,
        run_id=rec.current_run_id,
        url=url,
        error=None if restored else f"unknown state_id: {state_id}",
        data={"restored": restored, "state_id": state_id},
    )


async def handle_state_list(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_state_list", ok=False, error="session_id required")

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": "perception_state_list"}

    states = rec.state_manager.list_states()
    return make_envelope(
        "perception_state_list",
        ok=True,
        session_id=session_id,
        run_id=rec.current_run_id,
        data={"states": states, "count": len(states)},
    )


async def handle_flow_describe(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.perception.flow_graph import FLOWS

    flow_name = arguments.get("flow_name")
    if not flow_name:
        flows = {name: FLOWS[name]().description for name in FLOWS}
        return make_envelope(
            "perception_flow_describe",
            ok=True,
            data={"flows": flows, "flow_names": list(FLOWS.keys())},
        )

    name = str(flow_name)
    factory = FLOWS.get(name)
    if factory is None:
        return make_envelope(
            "perception_flow_describe",
            ok=False,
            error=f"unknown flow: {name}",
            data={"flow_names": list(FLOWS.keys())},
        )

    flow = factory()
    return make_envelope(
        "perception_flow_describe",
        ok=True,
        data={"flow": flow.to_dict()},
    )


async def handle_code_context(arguments: dict[str, Any]) -> dict[str, Any]:
    from pathlib import Path

    from navigation.codeGraph import create_code_graph

    repo_root = Path(str(arguments.get("repo_root") or "")).resolve() if arguments.get("repo_root") else None
    if repo_root is None:
        # Default: sandbox sibling of src/
        repo_root = Path(__file__).resolve().parents[3] / "sandbox"

    enabled = bool(arguments.get("enabled", True))
    query_type = str(arguments.get("query_type") or "stats")
    query_kwargs = dict(arguments.get("query_kwargs") or {})

    graph = create_code_graph(repo_root, enabled=enabled)
    result = graph.query(query_type, **query_kwargs)

    return make_envelope(
        "perception_code_context",
        ok=result.ok,
        error=result.error,
        data={
            "source": result.source,
            "summary": result.summary,
            "payload": result.payload,
            "repo_root": str(repo_root),
        },
    )


def _console_filter_from_args(arguments: dict[str, Any]) -> Any:
    from navigation.console.models import ConsoleFilter

    levels_raw = arguments.get("levels")
    levels = [str(x) for x in levels_raw] if isinstance(levels_raw, list) else None
    contains = arguments.get("contains")
    since_index = arguments.get("since_index")
    limit = int(arguments.get("limit", 100))
    return ConsoleFilter(
        levels=levels,
        contains=str(contains) if contains else None,
        since_index=int(since_index) if since_index is not None else None,
        limit=limit,
    )


async def handle_console_get(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_console_get", ok=False, error="session_id required")

    try:
        rec = store.require(session_id)
    except KeyError as exc:
        return make_envelope("perception_console_get", ok=False, error=str(exc))

    filt = _console_filter_from_args(arguments)
    since_index = arguments.get("since_index")
    report = rec.console.report(
        window_start_index=int(since_index) if since_index is not None else 0,
        filter=filt,
    )

    return make_envelope(
        "perception_console_get",
        session_id=session_id,
        run_id=rec.current_run_id,
        ok=True,
        data={"console": report.to_dict()},
    )


async def handle_console_clear(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_console_clear", ok=False, error="session_id required")

    try:
        rec = store.require(session_id)
    except KeyError as exc:
        return make_envelope("perception_console_clear", ok=False, error=str(exc))

    cleared = rec.console.clear()
    return make_envelope(
        "perception_console_clear",
        session_id=session_id,
        run_id=rec.current_run_id,
        ok=True,
        data={"cleared": cleared},
    )


def _network_filter_from_args(arguments: dict[str, Any]) -> Any:
    from navigation.network.models import NetworkFilter

    since_index = arguments.get("since_index")
    return NetworkFilter(
        status_min=int(arguments["status_min"]) if arguments.get("status_min") is not None else None,
        status_max=int(arguments["status_max"]) if arguments.get("status_max") is not None else None,
        failed_only=bool(arguments.get("failed_only", False)),
        api_group=str(arguments["api_group"]) if arguments.get("api_group") else None,
        contains=str(arguments["contains"]) if arguments.get("contains") else None,
        since_index=int(since_index) if since_index is not None else None,
        limit=int(arguments.get("limit", 50)),
        include_bodies=bool(arguments.get("include_bodies", False)),
    )


async def handle_network_get(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_network_get", ok=False, error="session_id required")

    try:
        rec = store.require(session_id)
    except KeyError as exc:
        return make_envelope("perception_network_get", ok=False, error=str(exc))

    filt = _network_filter_from_args(arguments)
    since_index = arguments.get("since_index")
    fetch_bodies = bool(arguments.get("include_bodies", False))
    report = await rec.network.report(
        rec.browser,
        window_start_index=int(since_index) if since_index is not None else 0,
        filter=filt,
        fetch_bodies=fetch_bodies,
    )

    return make_envelope(
        "perception_network_get",
        session_id=session_id,
        run_id=rec.current_run_id,
        ok=True,
        data={"network": report.to_dict()},
    )


async def handle_network_clear(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope("perception_network_clear", ok=False, error="session_id required")

    try:
        rec = store.require(session_id)
    except KeyError as exc:
        return make_envelope("perception_network_clear", ok=False, error=str(exc))

    cleared = rec.network.clear()
    return make_envelope(
        "perception_network_clear",
        session_id=session_id,
        run_id=rec.current_run_id,
        ok=True,
        data={"cleared": cleared},
    )


def _audit_agent_summary(report: Any) -> dict[str, Any]:
    advisory = [str(w.get("title") or w.get("id") or "") for w in report.warnings[:15] if w.get("title")]
    return {
        "blocking": list(report.blocking),
        "advisory": advisory,
        "audit": {
            "category": report.category,
            "score": report.score,
            "failed_count": report.audit_counts.get("failed", 0),
            "artifacts": dict(report.artifacts),
        },
    }


async def _handle_audit(
    store: SessionStore,
    arguments: dict[str, Any],
    category: Any,
    tool_name: str,
) -> dict[str, Any]:
    from navigation.audits.models import AuditCategory
    from navigation.audits.runner import LighthouseNotAvailableError
    from navigation.audits.service import run_audit

    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope(tool_name, ok=False, error="session_id required")

    try:
        rec = store.require(session_id)
    except KeyError as exc:
        return make_envelope(tool_name, ok=False, error=str(exc))

    url_arg = str(arguments.get("url") or "").strip()
    target_url = _resolve_url(rec.base_url, url_arg) if url_arg else None
    timeout_s = int(arguments.get("timeout_s", 120))

    try:
        report = await run_audit(
            rec.browser,
            category=category,
            base_url=rec.base_url,
            artifacts_dir=rec.artifacts_dir,
            url=target_url,
            timeout_s=timeout_s,
        )
    except LighthouseNotAvailableError as exc:
        return make_envelope(
            tool_name,
            ok=False,
            session_id=session_id,
            run_id=rec.current_run_id,
            error=str(exc),
            degraded=["lighthouse_unavailable"],
        )
    except Exception as exc:
        return make_envelope(
            tool_name,
            ok=False,
            session_id=session_id,
            run_id=rec.current_run_id,
            error=str(exc),
            degraded=["lighthouse_failed"],
        )

    audit_dict = report.to_dict()
    return make_envelope(
        tool_name,
        session_id=session_id,
        run_id=rec.current_run_id,
        url=audit_dict.get("url") or "",
        ok=True,
        data={
            "audit": audit_dict,
            "agent_summary": _audit_agent_summary(report),
        },
    )


async def handle_audit_accessibility(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.audits.models import AuditCategory

    return await _handle_audit(
        store,
        arguments,
        AuditCategory.ACCESSIBILITY,
        "perception_audit_accessibility",
    )


async def handle_audit_performance(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.audits.models import AuditCategory

    return await _handle_audit(
        store,
        arguments,
        AuditCategory.PERFORMANCE,
        "perception_audit_performance",
    )


async def handle_audit_seo(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.audits.models import AuditCategory

    return await _handle_audit(store, arguments, AuditCategory.SEO, "perception_audit_seo")


async def handle_audit_best_practices(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.audits.models import AuditCategory

    return await _handle_audit(
        store,
        arguments,
        AuditCategory.BEST_PRACTICES,
        "perception_audit_best_practices",
    )


def _diagnosis_options_from_args(arguments: dict[str, Any], *, mode: str) -> Any:
    from navigation.reports.models import DiagnosisOptions

    url_arg = str(arguments.get("url") or "").strip()
    include_shot = arguments.get("include_screenshot", True)
    if include_shot is False:
        include_shot = False
    run_audits = bool(arguments.get("run_audits", mode == "full"))
    return DiagnosisOptions(
        url=url_arg or None,
        include_screenshot=bool(include_shot),
        include_audits=run_audits and mode == "full",
        audit_timeout_s=int(arguments.get("timeout_s", 120)),
        mode=mode,
    )


async def _handle_diagnosis(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
    *,
    mode: str,
    tool_name: str,
) -> dict[str, Any]:
    from navigation.reports.diagnosis import (
        DiagnosisError,
        run_audit_mode,
        run_debug_mode,
        run_full_diagnosis,
    )

    session_id = str(arguments.get("session_id") or "")
    if not session_id:
        return make_envelope(tool_name, ok=False, error="session_id required")

    rec, err = _require_session(store, session_id)
    if err:
        return {**err, "tool": tool_name}

    options = _diagnosis_options_from_args(arguments, mode=mode)
    try:
        if mode == "debug":
            report = await run_debug_mode(rec, scans, session_id, options)
        elif mode == "audit":
            report = await run_audit_mode(rec, scans, session_id, options)
        else:
            report = await run_full_diagnosis(rec, scans, session_id, options)
    except DiagnosisError as exc:
        return make_envelope(
            tool_name,
            ok=False,
            session_id=session_id,
            run_id=rec.current_run_id,
            error=str(exc),
        )
    except Exception as exc:
        return make_envelope(
            tool_name,
            ok=False,
            session_id=session_id,
            run_id=rec.current_run_id,
            error=str(exc),
            degraded=["diagnosis_failed"],
        )

    report_dict = report.to_dict()
    summary = agent_summary_from_report(report_dict)
    envelope = make_envelope(
        tool_name,
        session_id=session_id,
        run_id=rec.current_run_id,
        scan_id=report.scan_id,
        url=report.url,
        degraded=report.degraded,
        data={
            "scan_id": report.scan_id,
            "perception_report": report_dict,
            "agent_summary": summary,
        },
    )
    scan_rec = scans.get(report.scan_id or "")
    if scan_rec and scan_rec.observation:
        return attach_observation_visuals(envelope, scan_rec.observation)
    return envelope


async def handle_full_diagnosis(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return await _handle_diagnosis(
        store,
        scans,
        arguments,
        mode="full",
        tool_name="perception_full_diagnosis",
    )


async def handle_debug_mode(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return await _handle_diagnosis(
        store,
        scans,
        arguments,
        mode="debug",
        tool_name="perception_debug_mode",
    )


async def handle_audit_mode(
    store: SessionStore,
    scans: ScanRegistry,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return await _handle_diagnosis(
        store,
        scans,
        arguments,
        mode="audit",
        tool_name="perception_audit_mode",
    )
