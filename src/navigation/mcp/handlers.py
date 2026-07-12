"""MCP tool handlers — thin wrappers over navigation.perception engine."""
from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from navigation.core.budget import OutputBudget, apply_observation_budget
from navigation.frontend_quality_intelligence.dev_insights import collect_dev_insights_during
from navigation.visual_browser_intelligence.observe.preflight import preflight_check, wait_for_page_ready
from navigation.visual_browser_intelligence.observe.scan import scan_page
from navigation.visual_browser_intelligence.verify.verification import SuccessCriteria, evaluate_js, verify

from navigation.core.envelope import agent_summary_from_observation, agent_summary_from_report, make_envelope
from navigation.core.paths import default_code_repo_root
from navigation.core.scan_registry import ScanRegistry
from navigation.frontend_quality_intelligence.diff import diff_observations
from navigation.visual_browser_intelligence.browser.session_store import SessionStore
from navigation.visual_browser_intelligence.visual.visual_response import (
	attach_diff_visuals,
	attach_observation_visuals,
	visual_uris_for_scan,
)


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
    from navigation.visual_browser_intelligence.observe.observation import collect_observation

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
    from navigation.visual_browser_intelligence.verify.verification import read_current_url

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
    from navigation.visual_browser_intelligence.observe.observation import collect_observation

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
    from navigation.visual_browser_intelligence.actions.scripted_actions import (
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
    from navigation.design_workflow_intelligence.state.auth_gate import check_auth_gate

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
    from navigation.component_intelligence.probes.form_probe import probe_validation_form

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
    from navigation.design_workflow_intelligence.state.route_guards import probe_maze_guards, probe_route_guard

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
        from navigation.design_workflow_intelligence.state.route_guards import GuardProbeResult

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
    from navigation.design_workflow_intelligence.flows.flow_graph import FLOWS

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

    from navigation.codebase_intelligence.graph import create_code_graph

    repo_root = Path(str(arguments.get("repo_root") or "")).resolve() if arguments.get("repo_root") else None
    if repo_root is None:
        repo_root = default_code_repo_root()

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
    from navigation.frontend_quality_intelligence.console.models import ConsoleFilter

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
    from navigation.frontend_quality_intelligence.network.models import NetworkFilter

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
    from navigation.frontend_quality_intelligence.audits.models import AuditCategory
    from navigation.frontend_quality_intelligence.audits.runner import LighthouseNotAvailableError
    from navigation.frontend_quality_intelligence.audits.service import run_audit

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
    from navigation.frontend_quality_intelligence.audits.models import AuditCategory

    return await _handle_audit(
        store,
        arguments,
        AuditCategory.ACCESSIBILITY,
        "perception_audit_accessibility",
    )


async def handle_audit_performance(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.frontend_quality_intelligence.audits.models import AuditCategory

    return await _handle_audit(
        store,
        arguments,
        AuditCategory.PERFORMANCE,
        "perception_audit_performance",
    )


async def handle_audit_seo(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.frontend_quality_intelligence.audits.models import AuditCategory

    return await _handle_audit(store, arguments, AuditCategory.SEO, "perception_audit_seo")


async def handle_audit_best_practices(store: SessionStore, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.frontend_quality_intelligence.audits.models import AuditCategory

    return await _handle_audit(
        store,
        arguments,
        AuditCategory.BEST_PRACTICES,
        "perception_audit_best_practices",
    )


def _diagnosis_options_from_args(arguments: dict[str, Any], *, mode: str) -> Any:
    from navigation.frontend_quality_intelligence.reports.models import DiagnosisOptions

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
    from navigation.frontend_quality_intelligence.reports.diagnosis import (
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


def _default_repo_root(arguments: dict[str, Any]) -> Path:
    raw = arguments.get("repo_root")
    if raw:
        return Path(str(raw)).resolve()
    return default_code_repo_root()


async def handle_detect_framework(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.framework_intelligence import FrameworkIntelligenceService

    repo_root = _default_repo_root(arguments)
    service = FrameworkIntelligenceService()
    metadata = service.detect(repo_root)
    return make_envelope(
        "perception_detect_framework",
        ok=metadata.framework is not None,
        degraded=metadata.degraded,
        data={
            "metadata": metadata.to_dict(),
            "agent_summary": {
                "framework": metadata.framework,
                "framework_version": metadata.framework_version,
                "primary_package": metadata.primary_package,
                "build_tool": metadata.build_tool,
                "package_manager": metadata.package_manager,
                "language": metadata.language,
                "is_monorepo": metadata.is_monorepo,
                "rendering_mode": metadata.rendering_mode,
                "router_mode": metadata.router_mode,
                "advisory": list(metadata.degraded),
            },
        },
    )


async def handle_search_components(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.component_intelligence import ComponentIntelligenceService

    query = str(arguments.get("query") or "").strip()
    if not query:
        return make_envelope("perception_search_components", ok=False, error="query required")

    search_plan = arguments.get("search_plan")
    if search_plan is not None and not isinstance(search_plan, dict):
        search_plan = None

    service = ComponentIntelligenceService()
    response = await service.search_components(query, search_plan=search_plan)
    ok = bool(response.candidates) or bool(response.degraded)
    return make_envelope(
        "perception_search_components",
        ok=ok,
        degraded=response.degraded,
        data={
            "component_search": response.to_dict(),
            "agent_summary": {
                "query": response.query.raw,
                "primary_intent": (response.search_plan.primary_intent if response.search_plan else query),
                "total": len(response.candidates),
                "providers_queried": response.providers_queried,
                "passes_executed": (
                    response.search_session.passes_executed if response.search_session else []
                ),
                "top_candidates": [c.to_dict() for c in response.candidates[:8]],
                "advisory": list(response.degraded),
            },
        },
    )


async def handle_plan_component_search(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.component_intelligence import ComponentIntelligenceService

    query = str(arguments.get("query") or "").strip()
    if not query:
        return make_envelope("perception_plan_component_search", ok=False, error="query required")

    service = ComponentIntelligenceService()
    plan = service.build_search_plan(query)
    return make_envelope(
        "perception_plan_component_search",
        ok=True,
        data={
            "search_plan": plan.to_dict(),
            "agent_summary": {
                "query": query,
                "primary_intent": plan.primary_intent,
                "planned_queries": [q.to_dict() for q in plan.planned_queries[:12]],
                "suggested_registries": plan.suggested_registries,
                "blocking": [],
                "advisory": [
                    "Host agent may refine this plan before calling perception_search_components.",
                    "Pass search_plan to perception_search_components to use a custom strategy.",
                ],
            },
        },
    )


async def handle_select_component_foundation(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.component_intelligence import ComponentIntelligenceService

    query = str(arguments.get("query") or "").strip()
    if not query:
        return make_envelope("perception_select_component_foundation", ok=False, error="query required")

    repo_root = _default_repo_root(arguments)
    search_plan = arguments.get("search_plan")
    if search_plan is not None and not isinstance(search_plan, dict):
        search_plan = None

    service = ComponentIntelligenceService()
    try:
        selection, search = await service.select_foundation(
            query,
            repo_root=repo_root,
            search_plan=search_plan,
            max_candidates=int(arguments.get("max_candidates") or 12),
        )
    except ValueError as exc:
        return make_envelope("perception_select_component_foundation", ok=False, error=str(exc))

    return make_envelope(
        "perception_select_component_foundation",
        ok=True,
        degraded=selection.degraded,
        data={
            "foundation_selection": selection.to_dict(),
            "component_search": search.to_dict(),
            "agent_summary": {
                "query": query,
                "chosen": selection.chosen.to_dict(),
                "synthesis": selection.guidance.synthesis.to_dict(),
                "rationale": selection.rationale,
                "runner_up_count": len(selection.runner_ups),
                "blocking": selection.guidance.framework.issues,
                "advisory": selection.guidance.framework.compatibility_warnings,
            },
        },
    )


async def handle_integrate_component(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.component_intelligence import ComponentIntelligenceService
    from navigation.component_intelligence.integration_models import IntegrationRequest

    query = str(arguments.get("query") or "").strip()
    candidate_id = str(arguments.get("candidate_id") or "").strip() or None
    if not query and not candidate_id:
        return make_envelope("perception_integrate_component", ok=False, error="query or candidate_id required")

    repo_root = _default_repo_root(arguments)
    search_plan = arguments.get("search_plan")
    if search_plan is not None and not isinstance(search_plan, dict):
        search_plan = None

    request = IntegrationRequest(
        query=query,
        candidate_id=candidate_id,
        repo_root=str(repo_root),
        preview_url=str(arguments.get("preview_url") or "").strip() or None,
        search_plan=search_plan,
        max_repair_attempts=int(arguments.get("max_repair_attempts") or 3),
        execute_install=bool(arguments.get("execute_install")),
        execute_repairs=bool(arguments.get("execute_repairs")),
    )

    service = ComponentIntelligenceService()
    result = await service.integrate_component(request)
    ok = result.status.value in ("completed", "degraded")
    return make_envelope(
        "perception_integrate_component",
        ok=ok,
        degraded=result.degraded,
        data={
            "integration_result": result.to_dict(),
            "agent_summary": {
                "status": result.status.value,
                "foundation": result.selection.chosen.to_dict() if result.selection else None,
                "validation_passed": result.validation.passed if result.validation else False,
                "repair_attempts": len(result.repair_attempts),
                "blocking": (result.validation.blocking if result.validation else []),
                "advisory": [
                    "Integration pipeline is partially scaffolded — install/validate/repair phases evolve in place.",
                    "Provide preview_url for browser validation when dev server is running.",
                ],
            },
        },
    )


async def handle_framework_docs(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.framework_intelligence import FrameworkIntelligenceService

    topic = str(arguments.get("topic") or "").strip()
    if not topic:
        return make_envelope("perception_framework_docs", ok=False, error="topic required")

    repo_root = _default_repo_root(arguments)
    use_cache = bool(arguments.get("use_cache", True))
    service = FrameworkIntelligenceService()
    response = await service.fetch_docs(repo_root, topic=topic, use_cache=use_cache)
    ok = bool(response.content.strip()) and 'docs_provider_unavailable' not in response.degraded
    return make_envelope(
        "perception_framework_docs",
        ok=ok,
        degraded=response.degraded,
        data={
            "framework_knowledge": response.to_dict(),
            "agent_summary": service.agent_summary_from_response(response),
        },
    )


def _inspiration_top_hits(candidates: list[Any], *, limit: int = 8) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ranked in candidates[:limit]:
        c = ranked.candidate
        out.append(
            {
                "title": c.title,
                "provider_id": c.provider_id,
                "url": c.url,
                "preview_ref": c.preview_ref,
                "overall_score": ranked.overall_score,
                "fetch_tier": c.metadata.get("fetch_tier", ""),
            }
        )
    return out


async def handle_inspiration_discover(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.inspiration_intelligence import InspirationDiscoveryRequest, InspirationIntelligenceService

    query = str(arguments.get("query") or "").strip()
    if not query:
        return make_envelope("perception_inspiration_discover", ok=False, error="query required")

    service = InspirationIntelligenceService()
    result = await service.discover(
        InspirationDiscoveryRequest(
            query=query,
            max_candidates=int(arguments.get("max_candidates") or 12),
            provider_preference=arguments.get("provider_preference"),
        )
    )
    ok = bool(result.candidates) or bool(result.degraded)
    blocking: list[str] = []
    if not result.candidates:
        blocking.append("no_inspiration_candidates")
    return make_envelope(
        "perception_inspiration_discover",
        ok=ok,
        degraded=result.degraded,
        data={
            "inspiration_discovery": result.to_dict(),
            "agent_summary": {
                "query": query,
                "total": len(result.candidates),
                "providers": list(result.search_plan.provider_ids),
                "top_hits": _inspiration_top_hits(result.candidates),
                "blocking": blocking,
                "advisory": [
                    "Read perception://inspiration-guide for per-site navigation and preview URL rules.",
                    "Call perception_inspiration_collect when you need agent_view_url + ephemeral vision blobs.",
                ],
            },
        },
    )


async def handle_inspiration_collect(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.inspiration_intelligence.collect import collect_inspiration_hits

    query = str(arguments.get("query") or "").strip()
    if not query:
        return make_envelope("perception_inspiration_collect", ok=False, error="query required")

    output_raw = str(arguments.get("output_dir") or "").strip()
    output_dir = Path(output_raw) if output_raw else None
    provider_ids = arguments.get("provider_ids")
    if provider_ids is not None and not isinstance(provider_ids, list):
        provider_ids = None

    manifest = await collect_inspiration_hits(
        query,
        output_dir,
        per_provider=int(arguments.get("per_provider") or 4),
        provider_ids=provider_ids,
        download_images=bool(arguments.get("download_images", False)),
        materialize_blobs=bool(arguments.get("materialize_blobs", True)),
        blob_session_id=arguments.get("blob_session_id"),
        write_per_hit_files=output_dir is not None,
    )
    hits = list(manifest.get("hits") or [])
    ok = bool(hits) or bool(manifest.get("provider_summary"))
    return make_envelope(
        "perception_inspiration_collect",
        ok=ok,
        data={
            "inspiration_collection": manifest,
            "agent_summary": {
                "query": query,
                "total_hits": manifest.get("total_hits", 0),
                "total_with_urls": manifest.get("total_with_urls", 0),
                "blob_session_id": manifest.get("blob_session_id", ""),
                "top_hits": hits[:8],
                "blocking": [] if hits else ["no_inspiration_hits"],
                "advisory": [
                    "Open agent_view_url for live pages; use inspiration_blob for vision.",
                    "Call perception_inspiration_session_end when design work is complete.",
                ],
            },
        },
    )


async def handle_inspiration_session_end(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.inspiration_intelligence import InspirationIntelligenceService

    session_id = str(arguments.get("session_id") or "").strip()
    if not session_id and not bool(arguments.get("cleanup_expired", False)):
        return make_envelope("perception_inspiration_session_end", ok=False, error="session_id required")

    service = InspirationIntelligenceService()
    if bool(arguments.get("cleanup_expired", False)):
        result = service.cleanup_inspiration_blobs()
        return make_envelope(
            "perception_inspiration_session_end",
            ok=True,
            data={"cleanup": result, "agent_summary": {"advisory": ["Expired blob sessions removed."]}},
        )

    result = service.end_inspiration_session(session_id)
    return make_envelope(
        "perception_inspiration_session_end",
        ok=True,
        data={
            "session_end": result,
            "agent_summary": {
                "session_id": session_id,
                "removed": result.get("removed", 0),
                "advisory": ["Ephemeral inspiration blobs deleted for this session."],
            },
        },
    )


def _resource_top_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for asset in assets[:8]:
        out.append(
            {
                "resource_id": asset.get("resource_id", ""),
                "provider_id": asset.get("provider_id", ""),
                "title": asset.get("title", ""),
                "preview_url": asset.get("preview_url", ""),
                "access_url": asset.get("access_url", ""),
                "format": asset.get("format", ""),
                "score": asset.get("score", 0),
            }
        )
    return out


def _build_resource_request(arguments: dict[str, Any], *, default_categories: list[str] | None = None) -> tuple[Any, str | None]:
    from navigation.resource_intelligence.models import ResourceCategory, ResourceDiscoveryRequest

    query = str(arguments.get("query") or "").strip()
    if not query:
        return None, "query required"
    categories: list[ResourceCategory] = []
    raw_cats = arguments.get("categories") or default_categories or []
    for raw in raw_cats:
        try:
            categories.append(ResourceCategory(str(raw)))
        except ValueError:
            continue
    request = ResourceDiscoveryRequest(
        query=query,
        categories=categories,
        max_results=int(arguments.get("max_results") or 12),
        provider_preference=arguments.get("provider_preference"),
        commercial_required=bool(arguments.get("commercial_required", True)),
        attribution_ok=bool(arguments.get("attribution_ok", True)),
        prefer_svg=bool(arguments.get("prefer_svg", True)),
        icon_family=arguments.get("icon_family"),
        icon_family_strict=bool(arguments.get("icon_family_strict", True)),
        allow_family_fallback=bool(arguments.get("allow_family_fallback", True)),
        persist_icon_family=bool(arguments.get("persist_icon_family", False)),
        repo_root=str(arguments.get("repo_root") or ""),
        project_id=str(arguments.get("project_id") or "default"),
        scan_id=arguments.get("scan_id"),
        design_sense_profile=arguments.get("design_sense_profile"),
        auto_observe_bridge=bool(arguments.get("auto_observe_bridge", False)),
    )
    return request, None


def _resource_search_envelope(tool: str, result: Any, query: str) -> dict[str, Any]:
    assets = [a.to_dict() for a in result.assets]
    ok = bool(assets) or bool(result.degraded)
    blocking: list[str] = []
    if not assets:
        blocking.append("no_resource_assets")
    advisory = [
        "Read perception://resource-guide for icon family + license rules.",
        "Icons in family: use verified_import / access_url — no blobs needed.",
    ]
    if not result.family_match:
        advisory.append("Family miss: use perception_resource_observe_bridge or reference_preview_url.")
    return make_envelope(
        tool,
        ok=ok,
        degraded=result.degraded,
        data={
            "resource_recommendation": result.to_dict(),
            "agent_summary": {
                "query": query,
                "icon_family": result.icon_family,
                "family_match": result.family_match,
                "fallback_used": result.fallback_used,
                "selection": result.selection.to_dict() if result.selection else None,
                "total": len(assets),
                "providers_queried": list(result.providers_queried),
                "license_warnings": list(result.license_warnings),
                "top_assets": _resource_top_assets(assets),
                "blocking": blocking,
                "advisory": advisory,
            },
        },
    )


async def handle_resource_search(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.resource_intelligence import ResourceIntelligenceService

    request, err = _build_resource_request(arguments)
    if err:
        return make_envelope("perception_resource_search", ok=False, error=err)
    service = ResourceIntelligenceService()
    result = await service.search(request)
    return _resource_search_envelope("perception_resource_search", result, request.query)


async def _resource_search_shortcut(
    tool_name: str, category: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Delegate to the shared search but preserve the specific tool name in the envelope."""
    args = dict(arguments)
    args.setdefault("categories", [category])
    envelope = await handle_resource_search(args)
    envelope = dict(envelope)
    envelope["tool"] = tool_name
    return envelope


async def handle_resource_icon_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _resource_search_shortcut("perception_resource_icon_search", "icon", arguments)


async def handle_resource_font_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _resource_search_shortcut("perception_resource_font_search", "font", arguments)


async def handle_resource_logo_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _resource_search_shortcut("perception_resource_logo_search", "logo", arguments)


async def handle_resource_photo_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _resource_search_shortcut("perception_resource_photo_search", "photo", arguments)


async def handle_resource_avatar_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _resource_search_shortcut("perception_resource_avatar_search", "avatar", arguments)


async def handle_resource_illustration_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _resource_search_shortcut(
        "perception_resource_illustration_search", "illustration", arguments
    )


async def handle_resource_pattern_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _resource_search_shortcut(
        "perception_resource_pattern_search", "pattern", arguments
    )


async def handle_resource_animation_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _resource_search_shortcut(
        "perception_resource_animation_search", "animation", arguments
    )


async def handle_resource_license_check(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.resource_intelligence import ResourceDiscoveryRequest, ResourceIntelligenceService

    asset = arguments.get("asset")
    if not isinstance(asset, dict):
        return make_envelope("perception_resource_license_check", ok=False, error="asset object required")
    request = ResourceDiscoveryRequest(
        query=str(arguments.get("query") or "license check"),
        commercial_required=bool(arguments.get("commercial_required", True)),
        attribution_ok=bool(arguments.get("attribution_ok", True)),
    )
    service = ResourceIntelligenceService()
    summary = service.check_license(asset, request)
    return make_envelope(
        "perception_resource_license_check",
        ok=True,
        data={"license_summary": summary, "agent_summary": {"allowed": summary.get("allowed", False)}},
    )


async def handle_resource_observe_bridge(scans: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.resource_intelligence import ResourceIntelligenceService

    scan_id = str(arguments.get("scan_id") or "").strip()
    query = str(arguments.get("query") or "").strip()
    if not scan_id or not query:
        return make_envelope("perception_resource_observe_bridge", ok=False, error="scan_id and query required")
    service = ResourceIntelligenceService()
    bridge = await service.resolve_from_observe(
        scan_id=scan_id,
        query=query,
        scans=scans,
        repo_root=str(arguments.get("repo_root") or ""),
        icon_family=arguments.get("icon_family"),
    )
    ok = bool(bridge.get("ok"))
    return make_envelope(
        "perception_resource_observe_bridge",
        ok=ok,
        degraded=list(bridge.get("degraded") or []),
        data={
            "resource_observe_bridge": bridge,
            "agent_summary": {
                "scan_id": scan_id,
                "query": query,
                "bridge": bridge.get("bridge", ""),
                "icon_family": bridge.get("icon_family"),
                "family_match": bridge.get("family_match", False),
                "selection": bridge.get("selection"),
                "blocking": [] if ok else ["resource_observe_bridge_miss"],
                "advisory": ["Use selection.verified_import or assets[0].access_url for integration."],
            },
        },
    )


async def handle_resource_preview(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.resource_intelligence.collect import collect_resource_assets

    query = str(arguments.get("query") or "").strip()
    if not query:
        return make_envelope("perception_resource_preview", ok=False, error="query required")

    categories = arguments.get("categories")
    asset_ids = arguments.get("asset_ids")
    if categories is not None and not isinstance(categories, list):
        categories = None
    if asset_ids is not None and not isinstance(asset_ids, list):
        asset_ids = None

    output_raw = str(arguments.get("output_dir") or "").strip()
    output_dir = Path(output_raw) if output_raw else None

    manifest = await collect_resource_assets(
        query,
        max_results=int(arguments.get("max_results") or 12),
        categories=[str(c) for c in categories] if categories else None,
        provider_preference=str(arguments.get("provider_preference") or "") or None,
        icon_family=arguments.get("icon_family"),
        icon_family_strict=bool(arguments.get("icon_family_strict", True)),
        allow_family_fallback=bool(arguments.get("allow_family_fallback", True)),
        persist_icon_family=bool(arguments.get("persist_icon_family", False)),
        materialize_blobs=arguments.get("materialize_blobs"),
        blob_fallback_only=bool(arguments.get("blob_fallback_only", True)),
        reference_preview_url=str(arguments.get("reference_preview_url") or ""),
        reference_image_path=str(arguments.get("reference_image_path") or ""),
        blob_session_id=arguments.get("blob_session_id"),
        output_dir=output_dir,
        asset_ids=[str(a) for a in asset_ids] if asset_ids else None,
        repo_root=str(arguments.get("repo_root") or ""),
    )
    hits = list(manifest.get("hits") or [])
    ok = bool(hits) or bool(manifest.get("providers_queried"))
    return make_envelope(
        "perception_resource_preview",
        ok=ok,
        data={
            "resource_collection": manifest,
            "agent_summary": {
                "query": query,
                "icon_family": manifest.get("icon_family", ""),
                "family_match": manifest.get("family_match", False),
                "total_hits": manifest.get("total_hits", 0),
                "total_with_urls": manifest.get("total_with_urls", 0),
                "blob_session_id": manifest.get("blob_session_id", ""),
                "license_warnings": manifest.get("license_warnings", []),
                "top_hits": hits[:8],
                "blocking": [] if hits else ["no_resource_hits"],
                "advisory": [
                    "In-family icons: use access_url / suggested_import — blobs skipped by default.",
                    "Family miss: pass reference_preview_url for vision blob; or perception_observe for OCR.",
                    "Call perception_resource_session_end when asset work is complete.",
                ],
            },
        },
    )


async def handle_resource_session_end(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.resource_intelligence import ResourceIntelligenceService

    session_id = str(arguments.get("session_id") or "").strip()
    if not session_id and not bool(arguments.get("cleanup_expired", False)):
        return make_envelope("perception_resource_session_end", ok=False, error="session_id required")

    service = ResourceIntelligenceService()
    if bool(arguments.get("cleanup_expired", False)):
        result = service.cleanup_resource_blobs()
        return make_envelope(
            "perception_resource_session_end",
            ok=True,
            data={"cleanup": result, "agent_summary": {"advisory": ["Expired resource blob sessions removed."]}},
        )

    result = service.end_resource_session(session_id)
    return make_envelope(
        "perception_resource_session_end",
        ok=True,
        data={
            "session_end": result,
            "agent_summary": {
                "session_id": session_id,
                "removed": result.get("removed", 0),
                "advisory": ["Ephemeral resource blobs deleted for this session."],
            },
        },
    )


async def handle_seo_status(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.seo_intelligence import SeoIntelligenceService

    service = SeoIntelligenceService()
    status = service.status()
    return make_envelope(
        "perception_seo_status",
        ok=True,
        data={
            "seo_status": status,
            "agent_summary": {
                "phase": status.get("phase"),
                "integrations": status.get("integrations"),
                    "advisory": [
                        "Read perception://seo-guide before SEO audits.",
                        "Default mode: development — Browser, Lighthouse, LibreCrawl, no auth.",
                        "Professional mode (mode=professional): GSC + GA4 — OAuth only when user asks.",
                    ],
            },
        },
    )


async def handle_seo_query(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.seo_intelligence import SeoIntelligenceService

    query_id = str(arguments.get("query_id") or "").strip()
    if not query_id:
        service = SeoIntelligenceService()
        return make_envelope(
            "perception_seo_query",
            ok=True,
            data={
                "seo_query": {"queries": service.list_graph_queries()},
                "agent_summary": {
                    "advisory": [
                        "Pass query_id e.g. page.issues, audit.diff, site.traffic_signals, graph.summary.",
                        "Run perception_seo_audit first to populate the graph.",
                    ],
                },
            },
        )

    params = arguments.get("params") if isinstance(arguments.get("params"), dict) else {}
    for key in ("page_url", "audit_id"):
        if arguments.get(key) and key not in params:
            params[key] = arguments.get(key)

    service = SeoIntelligenceService()
    outcome = service.graph_query(query_id, params)
    ok = bool(outcome.get("ok"))
    return make_envelope(
        "perception_seo_query",
        ok=ok,
        error=str(outcome.get("error") or "") if not ok else None,
        data={
            "seo_query": outcome,
            "agent_summary": {
                "query_id": query_id,
                "advisory": [
                    "Use page.issues before fixing a URL.",
                    "Use site.traffic_signals after professional audits for drop hypotheses.",
                ],
            },
        },
    )


async def handle_seo_connect(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.seo_intelligence.auth.bing import bing_auth_status
    from navigation.seo_intelligence.auth.connect import connect_bing, connect_google
    from navigation.seo_intelligence.auth.google import google_oauth_status
    from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

    onboarding = SeoOnboardingService()
    website_url = str(arguments.get("website_url") or arguments.get("url") or "").strip()
    code = str(arguments.get("code") or "").strip()
    api_key = str(arguments.get("api_key") or "").strip()
    provider = str(arguments.get("provider") or "").strip().lower()
    action = str(arguments.get("action") or "setup").strip().lower()
    interactive = bool(arguments.get("interactive", True))

    if action == "status" and not website_url:
        google_oauth = google_oauth_status()
        bing_oauth = bing_auth_status()
        return make_envelope(
            "perception_seo_connect",
            ok=True,
            data={
                "google_oauth": google_oauth,
                "bing_oauth": bing_oauth,
                "onboarding": {
                    "steps": ["website_url"],
                    "auth_on_demand": True,
                    "auth_flow": "local_browser_oauth",
                },
                "agent_summary": {
                    "advisory": [
                        "Initial setup: perception_seo_connect with website_url only.",
                        "Google/Bing OAuth only when user requests provider-specific analysis.",
                    ],
                },
            },
        )

    if not website_url:
        return make_envelope("perception_seo_connect", ok=False, error="website_url required")

    oauth_actions = {"connect_google", "connect_bing", "connect"}
    wants_google = action == "connect_google" or (action == "connect" and provider == "google")
    wants_bing = action == "connect_bing" or (action == "connect" and provider == "bing")

    if wants_bing or (provider == "bing" and action in oauth_actions):
        if api_key:
            try:
                result = await onboarding.complete_bing_api_key(website_url, api_key)
            except Exception as exc:
                return make_envelope("perception_seo_connect", ok=False, error=str(exc))
            profile = result.get("profile") or {}
            return make_envelope(
                "perception_seo_connect",
                ok=True,
                data={**result, "agent_summary": {"bing_connected": profile.get("bing_connected")}},
                degraded=list(result.get("discovery_notes") or []),
            )

        if code:
            try:
                result = await onboarding.complete_bing_connect(website_url, code)
            except Exception as exc:
                return make_envelope("perception_seo_connect", ok=False, error=str(exc))
            profile = result.get("profile") or {}
            return make_envelope(
                "perception_seo_connect",
                ok=True,
                data={**result, "agent_summary": {"bing_connected": profile.get("bing_connected")}},
                degraded=list(result.get("discovery_notes") or []),
            )

        if action == "refresh_discovery":
            try:
                profile = await onboarding.refresh_discovery(website_url, provider="bing")
            except Exception as exc:
                return make_envelope("perception_seo_connect", ok=False, error=str(exc))
            return make_envelope(
                "perception_seo_connect",
                ok=True,
                data={
                    "website_url": website_url,
                    "provider": "bing",
                    "profile": profile.to_dict(),
                    "discovery_notes": list(profile.discovery_notes),
                },
            )

        if interactive:
            try:
                result = await connect_bing(website_url, onboarding=onboarding)
            except Exception as exc:
                return make_envelope("perception_seo_connect", ok=False, error=str(exc))
            profile = result.get("profile") or {}
            return make_envelope(
                "perception_seo_connect",
                ok=True,
                data={
                    **result,
                    "agent_summary": {
                        "bing_connected": profile.get("bing_connected"),
                        "auth_flow": "local_browser_oauth",
                        "prompt": "Bing Webmaster connected.",
                    },
                },
                degraded=list(result.get("discovery_notes") or []),
            )

        try:
            auth = await onboarding.start_bing_connect(website_url)
        except Exception as exc:
            return make_envelope("perception_seo_connect", ok=False, error=str(exc))
        return make_envelope("perception_seo_connect", ok=True, data={**auth, "interactive": False})

    if wants_google:
        if code:
            try:
                result = await onboarding.complete_google_connect(website_url, code)
            except Exception as exc:
                return make_envelope("perception_seo_connect", ok=False, error=str(exc))
            profile = result.get("profile") or {}
            return make_envelope(
                "perception_seo_connect",
                ok=True,
                data={
                    **result,
                    "agent_summary": {
                        "google_connected": profile.get("google_connected"),
                        "auto_configured": profile.get("auto_configured"),
                        "prompt": "Google Search Console and Analytics connected.",
                    },
                },
                degraded=list(result.get("discovery_notes") or []),
            )

        if action == "refresh_discovery":
            try:
                profile = await onboarding.refresh_discovery(website_url, provider="google")
            except Exception as exc:
                return make_envelope("perception_seo_connect", ok=False, error=str(exc))
            return make_envelope(
                "perception_seo_connect",
                ok=True,
                data={
                    "website_url": website_url,
                    "profile": profile.to_dict(),
                    "discovery_notes": list(profile.discovery_notes),
                },
            )

        if interactive:
            try:
                result = await connect_google(website_url, onboarding=onboarding)
            except Exception as exc:
                return make_envelope("perception_seo_connect", ok=False, error=str(exc))
            profile = result.get("profile") or {}
            return make_envelope(
                "perception_seo_connect",
                ok=True,
                data={
                    **result,
                    "agent_summary": {
                        "google_connected": profile.get("google_connected"),
                        "auto_configured": profile.get("auto_configured"),
                        "auth_flow": "local_browser_oauth",
                        "prompt": "Google Search Console and Analytics connected.",
                    },
                },
                degraded=list(result.get("discovery_notes") or []),
            )

        try:
            auth = await onboarding.start_google_connect(website_url)
        except Exception as exc:
            return make_envelope("perception_seo_connect", ok=False, error=str(exc))
        return make_envelope("perception_seo_connect", ok=True, data={**auth, "interactive": False})

    if action == "refresh_discovery":
        try:
            profile = await onboarding.refresh_discovery(website_url)
        except Exception as exc:
            return make_envelope("perception_seo_connect", ok=False, error=str(exc))
        return make_envelope(
            "perception_seo_connect",
            ok=True,
            data={
                "website_url": website_url,
                "profile": profile.to_dict(),
                "discovery_notes": list(profile.discovery_notes),
            },
        )

    # Default: website-only setup (no OAuth)
    try:
        result = await onboarding.register_website(website_url)
    except Exception as exc:
        return make_envelope("perception_seo_connect", ok=False, error=str(exc))
    site = await onboarding.site_status(website_url)
    return make_envelope(
        "perception_seo_connect",
        ok=True,
        data={
            **result,
            **site,
            "agent_summary": {
                "ready": True,
                "advisory": [
                    "Website registered. SEO Intelligence ready without OAuth.",
                    "Connect Google only when user requests Search Console or GA4 analysis.",
                    "Connect Bing only when user requests Bing Webmaster analysis.",
                ],
            },
        },
    )


def _prepare_seo_audit_request(arguments: dict[str, Any]) -> tuple[Any, list[str]]:
    from navigation.seo_intelligence import SeoAuditRequest
    from navigation.seo_intelligence.planning.modes import parse_audit_mode
    from navigation.seo_intelligence.setup.onboarding import SeoOnboardingService

    website_url = str(arguments.get("website_url") or arguments.get("url") or "").strip()
    mode_raw = arguments.get("mode")
    mode = parse_audit_mode(str(mode_raw)) if mode_raw else None
    request = SeoAuditRequest(
        website_url=website_url,
        property_url=str(arguments.get("property_url") or ""),
        repo_root=str(arguments.get("repo_root") or ""),
        scan_id=str(arguments.get("scan_id") or ""),
        ga4_property_id=str(arguments.get("ga4_property_id") or ""),
        bing_site_url=str(arguments.get("bing_site_url") or ""),
        providers=[str(p) for p in (arguments.get("providers") or []) if p],
        intents=[str(i) for i in (arguments.get("intents") or []) if i],
        mode=mode,
        include_cross_analysis=bool(arguments.get("include_cross_analysis", True)),
        include_recommendations=bool(arguments.get("include_recommendations", True)),
        include_ai_visibility=bool(arguments.get("include_ai_visibility", True)),
        ai_reasoning=arguments.get("ai_reasoning") if "ai_reasoning" in arguments else None,
    )
    enriched, _profile, notes = SeoOnboardingService().enrich_audit_request(request)
    return enriched, notes


async def handle_seo_audit(scans: ScanRegistry, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.seo_intelligence import SeoIntelligenceService
    from navigation.seo_intelligence.planning.modes import mode_summary, resolve_effective_mode
    from navigation.seo_intelligence.setup.auth_requirements import auth_prompts_for_request, audit_blocked_by_auth

    website_url = str(arguments.get("website_url") or arguments.get("url") or "").strip()
    if not website_url:
        return make_envelope("perception_seo_audit", ok=False, error="website_url required")
    request, setup_notes = _prepare_seo_audit_request(arguments)
    effective_mode = resolve_effective_mode(request)

    if audit_blocked_by_auth(request):
        prompts = auth_prompts_for_request(request)
        return make_envelope(
            "perception_seo_audit",
            ok=False,
            error="auth_required",
            data={
                "auth_required": prompts,
                "mode": effective_mode.value,
                "agent_summary": {
                    "blocking": [p["prompt"] for p in prompts],
                    "advisory": [
                        "Professional SEO requires Google OAuth — run perception_seo_connect with action=connect_google (interactive opens browser).",
                        "Then retry perception_seo_audit with mode=professional.",
                    ],
                },
            },
        )

    service = SeoIntelligenceService(scan_registry=scans)
    result = await service.audit(request)
    payload = result.to_dict()
    advisory = [
        "Every recommendation must cite evidence_ids — run perception_seo_verify after fixes.",
        "Pass scan_id from perception_observe for Browser Intelligence rendering evidence.",
    ]
    if effective_mode.value == "development":
        advisory.append(
            "Development SEO mode (default) — no auth. Use mode=professional when user asks to optimize with Search Console data."
        )
    else:
        advisory.append("Professional SEO mode — live GSC/GA4 evidence included when connected.")
    if setup_notes:
        advisory.append(f"onboarding:{','.join(setup_notes[:3])}")
    if result.degraded:
        advisory.append(f"degraded:{','.join(result.degraded[:5])}")
    return make_envelope(
        "perception_seo_audit",
        ok=True,
        data={
            "seo_audit": payload,
            "mode": mode_summary(effective_mode),
            "agent_summary": {
                "website_url": website_url,
                "mode": effective_mode.value,
                "evidence_count": len(result.evidence),
                "recommendation_count": len(result.recommendations),
                "capability_routes": [r.to_dict() for r in result.capability_routes],
                "connections": result.connections,
                "advisory": advisory,
            },
        },
        degraded=result.degraded + setup_notes,
    )


async def handle_seo_verify(scans: ScanRegistry, arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.seo_intelligence import SeoIntelligenceService

    website_url = str(arguments.get("website_url") or arguments.get("url") or "").strip()
    if not website_url:
        return make_envelope("perception_seo_verify", ok=False, error="website_url required")
    request, _setup_notes = _prepare_seo_audit_request(arguments)
    rec_ids = [str(r) for r in (arguments.get("recommendation_ids") or []) if r]
    service = SeoIntelligenceService(scan_registry=scans)
    outcome = await service.verify(request, recommendation_ids=rec_ids)
    ok = bool(outcome.get("ok"))
    verification = outcome.get("verification") or {}
    return make_envelope(
        "perception_seo_verify",
        ok=ok,
        error=str(outcome.get("error") or "") if not ok else None,
        data={
            "seo_verify": outcome,
            "agent_summary": {
                "passed_count": verification.get("passed_count"),
                "failed_count": verification.get("failed_count"),
                "pending_resolved": verification.get("items"),
                "advisory": [
                    "Verification compares graph baseline to fresh audit evidence.",
                    "Also run perception_verify for UI-level confirmation.",
                ],
            },
        },
    )


async def handle_figma_status(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.figma_intelligence import FigmaIntelligenceService

    service = FigmaIntelligenceService()
    status = service.status()
    health = await service.health()
    return make_envelope(
        "perception_figma_status",
        ok=True,
        data={
            "figma_status": status,
            "health": health,
            "agent_summary": {
                "connected": status.get("connected"),
                "phase": status.get("phase"),
                "advisory": [
                    "Read perception://figma-guide before Figma tools.",
                    "Connect once with perception_figma_connect — PAT stored locally.",
                    "Use perception_figma_context for normalized design context.",
                ],
            },
        },
        degraded=list(health.get("degraded") or []),
    )


async def handle_figma_connect(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.figma_intelligence import FigmaIntelligenceService

    service = FigmaIntelligenceService()
    action = str(arguments.get("action") or "connect").strip().lower()
    pat = str(arguments.get("pat") or arguments.get("figma_pat") or arguments.get("token") or "").strip()
    account_hint = str(arguments.get("account_hint") or "").strip()

    if action in {"status", "check"}:
        conn = service.connection_status()
        return make_envelope(
            "perception_figma_connect",
            ok=True,
            data={
                "connection": conn,
                "agent_summary": {
                    "connected": conn.get("connected"),
                    "advisory": [
                        "Provide pat from Figma → Settings → Security → Personal access tokens.",
                        "User should only connect once unless token is invalid.",
                    ],
                },
            },
        )

    if action in {"disconnect", "clear"}:
        result = service.disconnect()
        return make_envelope(
            "perception_figma_connect",
            ok=True,
            data={"connection": result, "agent_summary": {"connected": False}},
        )

    if not pat:
        return make_envelope(
            "perception_figma_connect",
            ok=False,
            error="pat required — ask user for Figma Personal Access Token",
            data={
                "agent_summary": {
                    "advisory": [
                        "Prompt user: create PAT at Figma Settings → Security.",
                        "Retry perception_figma_connect with pat parameter.",
                    ],
                },
            },
        )

    try:
        result = await service.connect(pat, account_hint=account_hint)
    except Exception as exc:
        return make_envelope("perception_figma_connect", ok=False, error=str(exc))

    return make_envelope(
        "perception_figma_connect",
        ok=True,
        data={
            "connection": result,
            "agent_summary": {
                "connected": True,
                "advisory": ["Token stored locally. Use perception_figma_context next."],
            },
        },
    )


async def handle_figma_context(arguments: dict[str, Any]) -> dict[str, Any]:
    from navigation.figma_intelligence import FigmaIntelligenceService

    service = FigmaIntelligenceService()
    refresh = bool(arguments.get("refresh", False))
    file_key = str(arguments.get("file_key") or "").strip()
    file_url = str(arguments.get("file_url") or arguments.get("url") or "").strip()
    page_id = str(arguments.get("page_id") or arguments.get("active_page_id") or "").strip()
    frame_id = str(arguments.get("frame_id") or arguments.get("active_frame_id") or "").strip()
    file_name = str(arguments.get("file_name") or "").strip()
    selection = arguments.get("selection_node_ids") or arguments.get("node_ids") or []

    if file_key or file_url:
        service.set_active_file(file_key=file_key, file_url=file_url, file_name=file_name)
    if page_id:
        service.set_active_page(page_id)
    if frame_id:
        service.set_active_frame(frame_id)
    if selection:
        service.set_selection([str(n) for n in selection if n])

    if not service.connection_status().get("connected"):
        return make_envelope(
            "perception_figma_context",
            ok=False,
            error="figma_not_connected",
            data={
                "agent_summary": {
                    "advisory": ["Run perception_figma_connect with user PAT first."],
                },
            },
        )

    context = await service.get_context(refresh=refresh)
    payload = context.to_dict()
    advisory = []
    if context.degraded:
        advisory.append(f"degraded:{','.join(context.degraded[:5])}")
    if context.file is None:
        advisory.append("Set file_url or file_key to load a Figma file.")
    return make_envelope(
        "perception_figma_context",
        ok=True,
        data={
            "figma_context": payload,
            "agent_summary": {
                "connected": context.connected,
                "file_key": context.file.file_key if context.file else None,
                "component_count": len(context.components),
                "token_count": len(context.tokens),
                "cache_hit": bool((context.cache or {}).get("hit")),
                "advisory": advisory,
            },
        },
        degraded=list(context.degraded),
    )
