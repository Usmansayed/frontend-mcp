"""Visual diff artifacts — side-by-side and heatmap."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class VisualDiffResult:
	side_by_side_path: str | None = None
	heatmap_path: str | None = None
	pixel_change_ratio: float | None = None
	degraded: list[str] = field(default_factory=list)

	def to_dict(self) -> dict[str, Any]:
		return {
			'side_by_side_path': self.side_by_side_path,
			'heatmap_path': self.heatmap_path,
			'pixel_change_ratio': self.pixel_change_ratio,
			'degraded': list(self.degraded),
		}


def _pillow_available() -> bool:
	try:
		import PIL  # noqa: F401

		return True
	except ImportError:
		return False


def diff_screenshot_files(
	before_path: str | Path,
	after_path: str | Path,
	out_dir: Path,
	*,
	prefix: str = 'diff',
) -> VisualDiffResult:
	degraded: list[str] = []
	before = Path(before_path)
	after = Path(after_path)
	if not before.is_file() or not after.is_file():
		return VisualDiffResult(degraded=['screenshot_missing_for_visual_diff'])

	if not _pillow_available():
		return VisualDiffResult(degraded=['pillow_unavailable'])

	from PIL import Image, ImageChops, ImageDraw, ImageFont

	out_dir.mkdir(parents=True, exist_ok=True)
	img_a = Image.open(before).convert('RGB')
	img_b = Image.open(after).convert('RGB')

	# Normalize to same size (viewport resize between scans)
	w = max(img_a.width, img_b.width)
	h = max(img_a.height, img_b.height)

	def _pad(img: Image.Image) -> Image.Image:
		if img.size == (w, h):
			return img
		canvas = Image.new('RGB', (w, h), (30, 30, 30))
		canvas.paste(img, (0, 0))
		return canvas

	img_a = _pad(img_a)
	img_b = _pad(img_b)

	diff = ImageChops.difference(img_a, img_b)
	gray = diff.convert('L')
	hist = gray.histogram()
	total_pixels = w * h
	changed = total_pixels - (hist[0] if hist else 0)
	ratio = round(changed / total_pixels, 4) if total_pixels else 0.0

	# Heatmap: amplify diff
	heatmap = Image.eval(gray, lambda p: min(255, p * 4))
	heatmap_rgb = Image.merge('RGB', (heatmap, Image.new('L', heatmap.size, 0), Image.new('L', heatmap.size, 0)))
	heatmap_file = out_dir / f'{prefix}-heatmap.png'
	heatmap_rgb.save(heatmap_file)

	# Side-by-side with labels
	gap = 4
	label_h = 22
	canvas = Image.new('RGB', (w * 2 + gap, h + label_h), (20, 20, 20))
	canvas.paste(img_a, (0, label_h))
	canvas.paste(img_b, (w + gap, label_h))
	draw = ImageDraw.Draw(canvas)
	font = ImageFont.load_default()
	draw.text((8, 4), 'before', fill=(200, 200, 200), font=font)
	draw.text((w + gap + 8, 4), 'after', fill=(200, 200, 200), font=font)
	side_file = out_dir / f'{prefix}-side-by-side.png'
	canvas.save(side_file)

	return VisualDiffResult(
		side_by_side_path=str(side_file),
		heatmap_path=str(heatmap_file),
		pixel_change_ratio=ratio,
		degraded=degraded,
	)
