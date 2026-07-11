#!/usr/bin/env python3
"""Download inspiration preview images on demand from manifest or URL."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.inspiration_intelligence.tools.downloader import download_manifest, download_url, slugify
from navigation.inspiration_intelligence.tools.media_urls import image_extension, normalize_image_url


def main() -> int:
	parser = argparse.ArgumentParser(description='Download inspiration images from manifest or URL')
	parser.add_argument(
		'manifest',
		nargs='?',
		type=Path,
		help='Path to manifest.json from collect_inspiration.py',
	)
	parser.add_argument('--url', help='Single image URL to download')
	parser.add_argument('--output', '-o', type=Path, help='Output file path for --url mode')
	parser.add_argument('--referer', default='', help='Referer header for hotlinked images')
	parser.add_argument('--force', action='store_true', help='Re-download even if file exists')
	parser.add_argument('--medium', action='store_true', help='Use medium-quality CDN tier when downloading')
	args = parser.parse_args()

	if args.url:
		dest = args.output or Path(f'{slugify(args.url)}.{image_extension(args.url)}')
		ok = download_url(normalize_image_url(args.url), dest, referer=args.referer, root=ROOT)
		print(f'{"OK" if ok else "FAIL"} -> {dest}')
		return 0 if ok else 1

	if not args.manifest:
		parser.error('Provide manifest.json path or --url')
		return 2

	manifest = args.manifest.resolve()
	if not manifest.is_file():
		print(f'Not found: {manifest}')
		return 1

	summary = download_manifest(
		manifest,
		manifest.parent,
		only_missing=not args.force,
		medium=args.medium,
	)
	print(f"Downloaded: {summary.get('downloaded', 0)} | failed: {summary.get('failed', 0)}")
	print(f'Manifest updated: {manifest}')
	return 0 if summary.get('failed', 0) == 0 else 1


if __name__ == '__main__':
	raise SystemExit(main())
