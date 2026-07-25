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


def _rect_box(rect: dict[str, Any], max_w: int, max_h: int) -> tuple[int, int, int, int] | None:
	"""DOM rect (CSS px, scroll-0 == page coords) → PIL crop box, clamped to image."""
	try:
		x = max(0, int(rect.get('x', rect.get('left', 0))))
		y = max(0, int(rect.get('y', rect.get('top', 0))))
		# Layout regions use w/h; element clips use width/height.
		w = int(rect.get('width', rect.get('w', 0)))
		h = int(rect.get('height', rect.get('h', 0)))
	except (TypeError, ValueError):
		return None
	if w < 8 or h < 8:
		return None
	right = min(max_w, x + w)
	bottom = min(max_h, y + h)
	if right <= x or bottom <= y:
		return None
	return (x, y, right, bottom)


async def capture_design_evidence(
	session: Any,
	images_dir: Path,
	name: str,
	*,
	regions: list[dict[str, Any]] | None = None,
	selector: str | None = None,
	max_sections: int = 3,
	annotate: bool = True,
	extra_labels: list[str] | None = None,
	want_viewport: bool = True,
	want_full: bool = True,
	want_sections: bool = True,
	want_element: bool = True,
	prefer_sections: list[str] | None = None,
) -> tuple[list[tuple[str, str]], list[str]]:
	"""Capture a design-evidence pack: annotated viewport + full page + section crops.

	Pack flags let callers request only what is owed (viewport / full / section / element).
	Section crops are cut from the full-page PNG with Pillow using DOM region rects
	(device scale factor is 1.0 in this runtime). Fully best-effort.
	"""
	images_dir.mkdir(parents=True, exist_ok=True)
	paths: list[tuple[str, str]] = []
	degraded: list[str] = []
	prefer = {str(s).strip().lower() for s in (prefer_sections or []) if str(s).strip()}

	# 1. Viewport (annotated preferred — element boxes + labels help the agent).
	if want_viewport:
		try:
			vp = await capture_visuals(
				session,
				images_dir,
				f'{name}-viewport',
				mode='viewport',
				annotate=annotate,
				extra_labels=extra_labels,
			)
			degraded.extend(vp.degraded)
			if vp.annotated_screenshot_path:
				paths.append(('viewport_annotated', vp.annotated_screenshot_path))
			elif vp.screenshot_path:
				paths.append(('viewport', vp.screenshot_path))
		except Exception:
			degraded.append('viewport_capture_failed')

	# 2. Explicit element crop (agent is editing a specific element).
	if want_element and selector:
		try:
			el = await capture_visuals(
				session,
				images_dir,
				f'{name}-element',
				mode='element',
				selector=selector,
				annotate=False,
			)
			degraded.extend(el.degraded)
			if el.crop_screenshot_path:
				paths.append((f'element:{selector[:40]}', el.crop_screenshot_path))
		except Exception:
			degraded.append('element_capture_failed')

	# 3. Full page + section crops.
	need_full = want_full or (want_sections and max_sections > 0)
	if need_full:
		try:
			full_bytes = await _take_bytes(session, full_page=True)
		except Exception:
			full_bytes = None
		if full_bytes:
			full_path = images_dir / f'{name}-full.png'
			full_path.write_bytes(full_bytes)
			if want_full:
				paths.append(('full_page', str(full_path)))
			if want_sections and regions and max_sections > 0 and _pillow_available():
				try:
					import io

					from PIL import Image

					img = Image.open(io.BytesIO(full_bytes)).convert('RGB')
					max_w, max_h = img.size
					count = 0
					seen: set[str] = set()
					# Prefer agent-flagged sections first, then remaining regions.
					ordered = list(regions)
					if prefer:
						ordered = sorted(
							ordered,
							key=lambda r: (
								0
								if str((r or {}).get('label') or (r or {}).get('role') or '')
								.lower()
								in prefer
								else 1
							),
						)
					for region in ordered:
						if count >= max_sections:
							break
						if not isinstance(region, dict):
							continue
						rect = region.get('rect')
						if not isinstance(rect, dict):
							continue
						box = _rect_box(rect, max_w, max_h)
						if box is None:
							continue
						label = str(region.get('label') or region.get('role') or f'section{count}')
						dedupe = f'{label}:{box[1]}:{box[3]}'
						if dedupe in seen:
							continue
						seen.add(dedupe)
						safe = ''.join(ch if ch.isalnum() else '-' for ch in label)[:24] or f'section{count}'
						section_path = images_dir / f'{name}-section-{count}-{safe}.png'
						img.crop(box).save(section_path, format='PNG')
						paths.append((f'section:{label}', str(section_path)))
						count += 1
				except Exception:
					degraded.append('section_crop_failed')
		else:
			degraded.append('full_page_failed')

	return paths, sorted(set(degraded))
