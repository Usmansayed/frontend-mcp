"""Phase 1: unified page observation for coding-agent insights."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navigation.frontend_quality_intelligence.dev_insights import (
	DevInsights,
	DevInsightsCollector,
	wait_for_edge_lab_collector_signals,
)
from navigation.visual_browser_intelligence.verify.verification import evaluate_js, read_current_url, read_page_text
from navigation.visual_browser_intelligence.visual.visual_capture import ScreenshotMode, VisualCaptureResult, capture_visuals


@dataclass(slots=True)
class PageObservation:
	url: str
	a11y_tree: str
	dom_text: str
	screenshot_path: str | None = None
	annotated_screenshot_path: str | None = None
	crop_screenshot_path: str | None = None
	console: list[str] = field(default_factory=list)
	network: list[dict[str, Any]] = field(default_factory=list)
	dev_insights: DevInsights | None = None
	console_report: dict[str, Any] | None = None
	network_report: dict[str, Any] | None = None
	visual_insights: dict[str, Any] | None = None
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		out: dict[str, Any] = {
			'url': self.url,
			'a11y_tree': self.a11y_tree[:8000],
			'dom_text': self.dom_text[:8000],
			'screenshot_path': self.screenshot_path,
			'annotated_screenshot_path': self.annotated_screenshot_path,
			'crop_screenshot_path': self.crop_screenshot_path,
			'degraded': list(self.degraded),
		}
		if self.network_report is not None:
			out['network'] = self.network_report
		elif self.network:
			out['network_failures'] = self.network
		if self.console_report is not None:
			out['console'] = self.console_report
		elif self.console:
			out['console_errors'] = self.console
		if self.dev_insights is not None:
			out['dev_insights'] = self.dev_insights.to_dict()
		if self.visual_insights is not None:
			out['visual_insights'] = self.visual_insights
		return out


async def collect_observation(
	session: Any,
	*,
	images_dir: Path | None = None,
	name: str = 'page',
	capture_dev_insights: bool = True,
	console_service: Any | None = None,
	console_window_start: int | None = None,
	network_service: Any | None = None,
	network_window_start: int | None = None,
	har_dir: Path | None = None,
	screenshot_mode: ScreenshotMode = 'viewport',
	screenshot_selector: str | None = None,
	annotate_screenshot: bool = True,
	extra_visual_labels: list[str] | None = None,
) -> PageObservation:
	degraded: list[str] = []
	if console_service is not None and console_window_start is None:
		console_window_start = console_service.mark_window()
	if network_service is not None and network_window_start is None:
		network_window_start = network_service.mark_window()
	collector: DevInsightsCollector | None = None
	if capture_dev_insights:
		collector = DevInsightsCollector()
		await collector.start(session)

	url = await read_current_url(session)
	a11y = ''
	try:
		a11y = await session.get_state_as_text()
	except Exception:
		degraded.append('a11y_unavailable')

	dom_text = await read_page_text(session, include_dom_text=True)
	inner = await evaluate_js(session, 'document.body.innerText')
	if inner and str(inner) not in dom_text:
		dom_text = f'{dom_text}\n{inner}'
	if not dom_text.strip():
		degraded.append('dom_text_empty')

	screenshot_path: str | None = None
	annotated_path: str | None = None
	crop_path: str | None = None
	visual_insights_dict: dict[str, Any] | None = None

	if images_dir is not None:
		visual: VisualCaptureResult = await capture_visuals(
			session,
			images_dir,
			name,
			mode=screenshot_mode,
			selector=screenshot_selector,
			annotate=annotate_screenshot,
			extra_labels=extra_visual_labels,
			collect_insights=True,
		)
		screenshot_path = visual.screenshot_path
		annotated_path = visual.annotated_screenshot_path
		crop_path = visual.crop_screenshot_path
		if visual.visual_insights is not None:
			visual_insights_dict = visual.visual_insights.to_dict()
		degraded.extend(visual.degraded)

	dev_insights = None
	if collector:
		await wait_for_edge_lab_collector_signals(collector, url)
		await collector.snapshot_page_signals(session)
		dev_insights = collector.stop(url=url)
		degraded.extend(dev_insights.degraded)

	console_lines = [e.text for e in dev_insights.console_errors] if dev_insights else []
	network_lines = [n.to_dict() for n in dev_insights.network_failures] if dev_insights else []

	console_report: dict[str, Any] | None = None
	if console_service is not None and console_window_start is not None:
		console_report = console_service.window_report(console_window_start).to_dict()

	network_report: dict[str, Any] | None = None
	if network_service is not None and network_window_start is not None:
		har_target = har_dir
		if har_target is None and images_dir is not None:
			har_target = images_dir.parent / 'network'
		net = await network_service.window_report(
			session,
			network_window_start,
			page_url=url,
			har_dir=har_target,
			har_name=name,
		)
		network_report = net.to_dict()

	return PageObservation(
		url=url,
		a11y_tree=a11y or '',
		dom_text=dom_text or '',
		screenshot_path=screenshot_path,
		annotated_screenshot_path=annotated_path,
		crop_screenshot_path=crop_path,
		console=console_lines,
		network=network_lines,
		dev_insights=dev_insights,
		console_report=console_report,
		network_report=network_report,
		visual_insights=visual_insights_dict,
		degraded=sorted(set(degraded)),
	)
