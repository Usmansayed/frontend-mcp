"""Screenshot capture, annotation, and region crops."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from navigation.design_sense_intelligence.heuristics.visual_insights import VisualInsights, collect_visual_insights

ScreenshotMode = Literal['viewport', 'full', 'element']


@dataclass(slots=True)
class VisualCaptureResult:
	screenshot_path: str | None = None
	annotated_screenshot_path: str | None = None
	crop_screenshot_path: str | None = None
	extra_screenshot_paths: list[str] = field(default_factory=list)
	visual_insights: VisualInsights | None = None
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		out: dict[str, Any] = {
			'screenshot_path': self.screenshot_path,
			'annotated_screenshot_path': self.annotated_screenshot_path,
			'crop_screenshot_path': self.crop_screenshot_path,
			'extra_screenshot_paths': list(self.extra_screenshot_paths),
			'degraded': list(self.degraded),
		}
		if self.visual_insights is not None:
			out['visual_insights'] = self.visual_insights.to_dict()
		return out


def _pillow_available() -> bool:
	try:
		import PIL  # noqa: F401

		return True
	except ImportError:
		return False


async def _take_bytes(
	session: Any,
	*,
	full_page: bool = False,
	clip: dict[str, int] | None = None,
) -> bytes | None:
	try:
		data = await session.take_screenshot(full_page=full_page, clip=clip)
	except TypeError:
		# Older browser-use without clip kwarg
		if clip is not None:
			return None
		data = await session.take_screenshot(full_page=full_page)
	except Exception:
		return None

	if isinstance(data, str):
		return base64.b64decode(data)
	if isinstance(data, (bytes, bytearray)):
		return bytes(data)
	return None


async def _element_clip(session: Any, selector: str) -> dict[str, int] | None:
	from .verification import evaluate_js

	js = f"""(() => {{
	  const el = document.querySelector({selector!r});
	  if (!el) return null;
	  const r = el.getBoundingClientRect();
	  if (r.width < 1 || r.height < 1) return null;
	  const pad = 8;
	  return {{
	    x: Math.max(0, Math.floor(r.x - pad)),
	    y: Math.max(0, Math.floor(r.y - pad)),
	    width: Math.ceil(r.width + pad * 2),
	    height: Math.ceil(r.height + pad * 2),
	  }};
	}})()"""
	raw = await evaluate_js(session, js)
	if not isinstance(raw, dict):
		return None
	try:
		return {
			'x': int(raw['x']),
			'y': int(raw['y']),
			'width': max(1, int(raw['width'])),
			'height': max(1, int(raw['height'])),
		}
	except (KeyError, TypeError, ValueError):
		return None


def _annotate_png(
	path: Path,
	boxes: list[dict[str, Any]],
	*,
	extra_labels: list[str] | None = None,
	out_path: Path | None = None,
) -> Path | None:
	if not _pillow_available() or not path.is_file():
		return None

	from PIL import Image, ImageDraw, ImageFont

	img = Image.open(path).convert('RGBA')
	overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
	draw = ImageDraw.Draw(overlay)
	font = ImageFont.load_default()

	for box in boxes:
		highlight = str(box.get('highlight') or '')
		role = str(box.get('role') or '')
		if highlight == 'blocking' or role == 'error':
			color = (220, 38, 38, 200)
		elif box.get('interactive'):
			color = (34, 197, 94, 140)
		else:
			color = (59, 130, 246, 120)

		x = int(box.get('x', 0))
		y = int(box.get('y', 0))
		w = int(box.get('width', 1))
		h = int(box.get('height', 1))
		draw.rectangle([x, y, x + w, y + h], outline=color[:3] + (255,), width=2)
		label = str(box.get('label') or '')[:32]
		if label:
			draw.rectangle([x, max(0, y - 14), x + min(220, len(label) * 7 + 8), y], fill=color)
			draw.text((x + 2, max(0, y - 12)), label, fill=(255, 255, 255, 255), font=font)

	y_off = 8
	for text in extra_labels or []:
		line = str(text)[:80]
		draw.rectangle([8, y_off, 8 + len(line) * 7 + 8, y_off + 16], fill=(220, 38, 38, 220))
		draw.text((12, y_off + 2), line, fill=(255, 255, 255, 255), font=font)
		y_off += 20

	composed = Image.alpha_composite(img, overlay).convert('RGB')
	target = out_path or path.with_name(f'{path.stem}-annotated{path.suffix}')
	composed.save(target, format='PNG')
	return target


async def capture_visuals(
	session: Any,
	images_dir: Path,
	name: str,
	*,
	mode: ScreenshotMode = 'viewport',
	selector: str | None = None,
	annotate: bool = True,
	extra_labels: list[str] | None = None,
	collect_insights: bool = True,
) -> VisualCaptureResult:
	degraded: list[str] = []
	images_dir.mkdir(parents=True, exist_ok=True)
	base_path = images_dir / f'{name}.png'

	visual = await collect_visual_insights(session) if collect_insights else None
	clip: dict[str, int] | None = None
	full_page = mode == 'full'

	if mode == 'element':
		if not selector:
			degraded.append('element_screenshot_no_selector')
		else:
			clip = await _element_clip(session, selector)
			if clip is None:
				degraded.append('element_screenshot_selector_miss')

	raw_bytes = await _take_bytes(session, full_page=full_page, clip=clip)
	if raw_bytes is None:
		return VisualCaptureResult(visual_insights=visual, degraded=sorted(set(degraded + ['screenshot_failed'])))

	base_path.write_bytes(raw_bytes)
	screenshot_path = str(base_path)

	crop_path: str | None = None
	if mode == 'element' and clip is not None:
		crop_file = images_dir / f'{name}-crop.png'
		crop_file.write_bytes(raw_bytes)
		crop_path = str(crop_file)

	annotated_path: str | None = None
	if annotate and visual is not None:
		boxes = list(visual.element_boxes)
		ann = _annotate_png(
			base_path,
			boxes,
			extra_labels=extra_labels,
			out_path=images_dir / f'{name}-annotated.png',
		)
		if ann is not None:
			annotated_path = str(ann)
		elif annotate:
			degraded.append('annotation_skipped')

	if not _pillow_available():
		degraded.append('pillow_unavailable')

	return VisualCaptureResult(
		screenshot_path=screenshot_path,
		annotated_screenshot_path=annotated_path,
		crop_screenshot_path=crop_path,
		visual_insights=visual,
		degraded=sorted(set(degraded)),
	)
