#!/usr/bin/env python3
"""End or expire ephemeral inspiration blob sessions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from navigation.inspiration_intelligence import InspirationIntelligenceService


def main() -> int:
	parser = argparse.ArgumentParser(description='Clean up ephemeral inspiration blob sessions')
	parser.add_argument('--session', help='End a specific blob session id')
	parser.add_argument('--expired', action='store_true', help='Remove all TTL-expired sessions')
	parser.add_argument('--list', action='store_true', help='List active blob sessions')
	args = parser.parse_args()

	service = InspirationIntelligenceService()

	if args.list:
		sessions = service.list_inspiration_sessions()
		print(json.dumps(sessions, indent=2))
		return 0

	if args.session:
		result = service.end_inspiration_session(args.session)
		print(json.dumps(result, indent=2))
		return 0

	if args.expired:
		result = service.cleanup_inspiration_blobs()
		print(json.dumps(result, indent=2))
		return 0

	parser.print_help()
	return 2


if __name__ == '__main__':
	raise SystemExit(main())
