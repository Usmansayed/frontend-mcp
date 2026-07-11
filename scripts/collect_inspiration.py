#!/usr/bin/env python3
"""Collect inspiration URLs from all providers — agents open URLs directly; download optional."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.inspiration_intelligence.collect import collect_inspiration_hits
from navigation.inspiration_intelligence.tools.downloader import slugify


def main() -> int:
	parser = argparse.ArgumentParser(description='Collect inspiration URLs from all providers')
	parser.add_argument('query', nargs='?', default='saas landing page')
	parser.add_argument('--output', '-o', type=Path, default=None)
	parser.add_argument('--providers', nargs='*', default=None, help='Subset of provider ids')
	parser.add_argument('--per-provider', type=int, default=4)
	parser.add_argument(
		'--download',
		action='store_true',
		help='Also download preview images to disk (optional; default is URLs only)',
	)
	parser.add_argument(
		'--no-blobs',
		action='store_true',
		help='Skip ephemeral medium-quality JPEG blobs for agent vision',
	)
	parser.add_argument('--session-id', default=None, help='Reuse an existing blob session id')
	args = parser.parse_args()

	stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
	out = args.output or (ROOT / 'artifacts' / 'inspiration_collections' / f'{slugify(args.query)}_{stamp}')

	import os

	os.environ.setdefault('INSPIRATION_FORCE', '1')
	os.environ.setdefault('INSPIRATION_FAST', '0')
	os.environ.setdefault('INSPIRATION_HEADLESS', 'false')

	print(f'Query: {args.query!r}')
	print(f'Output: {out}')
	blobs_on = not args.no_blobs
	mode_bits = ['urls']
	if blobs_on:
		mode_bits.append('ephemeral blobs')
	if args.download:
		mode_bits.append('permanent download')
	print(f'Mode: {" + ".join(mode_bits)}')
	manifest = asyncio.run(
		collect_inspiration_hits(
			args.query,
			out,
			per_provider=args.per_provider,
			provider_ids=args.providers,
			download_images=args.download,
			materialize_blobs=blobs_on,
			blob_session_id=args.session_id,
		)
	)
	if blobs_on and manifest.get('blob_session_id'):
		bs = manifest.get('blob_summary') or {}
		print(
			f"\nBlobs: {bs.get('materialized', 0)} materialized | "
			f"failed: {bs.get('failed', 0)} | session: {manifest.get('blob_session_id')}"
		)
		print(
			'End session when done: python scripts/inspiration_blob_cleanup.py --session',
			manifest.get('blob_session_id'),
		)
	print('\n=== DONE ===')
	print(f"Hits: {manifest['total_hits']} | With URLs: {manifest['total_with_urls']}")
	print(f"Manifest: {out / 'manifest.json'}")
	return 0 if manifest['total_hits'] else 1


if __name__ == '__main__':
	raise SystemExit(main())
