"""Deterministic HTTP scrape → raw/ + manifest + checksum."""
from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from bs4 import BeautifulSoup

from .paths import PASS1_SOURCES, PASS2_SOURCES, RAW, RESOURCES, pass_sources_path

USER_AGENT = (
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
	"(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def load_pass(pass_num: int = 1) -> list[dict[str, Any]]:
	path = pass_sources_path(pass_num)
	data = yaml.safe_load(path.read_text(encoding="utf-8"))
	return list(data["sources"])


def load_pass1() -> list[dict[str, Any]]:
	return load_pass(1)


def html_to_markdownish(html: str, url: str) -> str:
	soup = BeautifulSoup(html, "html.parser")
	for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
		tag.decompose()
	title = (soup.title.string or "").strip() if soup.title else ""
	main = soup.find("main") or soup.find("article") or soup.body or soup
	text = main.get_text("\n", strip=True)
	# collapse excess blank lines
	text = re.sub(r"\n{3,}", "\n\n", text)
	header = f"# {title or urlparse(url).path}\n\nSource: {url}\nFetched: {date.today().isoformat()}\n\n"
	return header + text


def fetch_url(url: str, timeout: float = 45.0) -> tuple[str, str]:
	"""Return (content_type, body_text_or_html)."""
	headers = {
		"User-Agent": USER_AGENT,
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
		"Accept-Language": "en-US,en;q=0.9",
	}
	with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
		resp = client.get(url)
		resp.raise_for_status()
		ctype = resp.headers.get("content-type", "text/html").split(";")[0].strip()
		return ctype, resp.text


def sha256_bytes(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()


def write_manifest(
	source_id: str,
	url: str,
	artifact_name: str,
	checksum: str,
	nbytes: int,
	*,
	notes: str = "",
) -> Path:
	dest = RAW / source_id
	dest.mkdir(parents=True, exist_ok=True)
	manifest = {
		"source_id": source_id,
		"acquired_at": date.today().isoformat(),
		"acquired_by": "foropencode_pipeline",
		"url": url,
		"access": "public",
		"license_notes": "Snapshot for internal research corpus; respect source ToS.",
		"artifacts": [
			{
				"path": artifact_name,
				"content_type": "text/markdown" if artifact_name.endswith(".md") else "text/html",
				"checksum_sha256": checksum,
				"bytes": nbytes,
			}
		],
		"pointers": [{"kind": "canonical_url", "value": url}],
		"notes": notes,
	}
	path = dest / "manifest.yaml"
	path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
	return path


def scrape_source(entry: dict[str, Any]) -> dict[str, Any]:
	source_id = entry["source_id"]
	min_bytes = int(entry.get("min_bytes", 2000))
	last_err: Exception | None = None
	for url in entry["urls"]:
		try:
			ctype, body = fetch_url(url)
			# raw.githubusercontent / plain text
			if "html" in ctype or body.lstrip().startswith("<!") or body.lstrip().startswith("<html"):
				md = html_to_markdownish(body, url)
				html_path = RAW / source_id / "snapshot.html"
				html_path.parent.mkdir(parents=True, exist_ok=True)
				html_bytes = body.encode("utf-8", errors="replace")
				html_path.write_bytes(html_bytes)
				content = md
				artifact = "snapshot.md"
			else:
				content = f"# {source_id}\n\nSource: {url}\nFetched: {date.today().isoformat()}\n\n{body}"
				artifact = "snapshot.md"
			data = content.encode("utf-8")
			if len(data) < min_bytes:
				last_err = RuntimeError(f"{url} too small: {len(data)} < {min_bytes}")
				continue
			dest = RAW / source_id
			dest.mkdir(parents=True, exist_ok=True)
			snap = dest / artifact
			snap.write_bytes(data)
			checksum = sha256_bytes(data)
			write_manifest(
				source_id,
				url,
				artifact,
				checksum,
				len(data),
				notes=str(entry.get("notes") or ""),
			)
			# cleanup old stub sidecars
			for junk in ("sha.txt", "hash.txt"):
				p = dest / junk
				if p.exists():
					p.unlink()
			return {
				"source_id": source_id,
				"url": url,
				"bytes": len(data),
				"checksum_sha256": checksum,
				"path": str(snap),
				"ok": True,
			}
		except Exception as exc:  # noqa: BLE001 — collect and try next URL
			last_err = exc
			continue
	return {
		"source_id": source_id,
		"ok": False,
		"error": str(last_err) if last_err else "all urls failed",
	}


def scrape_pass(pass_num: int = 1) -> list[dict[str, Any]]:
	results = []
	for entry in load_pass(pass_num):
		results.append(scrape_source(entry))
	return results


def scrape_pass1() -> list[dict[str, Any]]:
	return scrape_pass(1)


def mark_acquired(source_ids: list[str]) -> list[str]:
	"""Flip RESOURCE_INDEX status to acquired for given ids; clear false rejections."""
	index_path = RESOURCES / "RESOURCE_INDEX.yaml"
	text = index_path.read_text(encoding="utf-8")
	data = yaml.safe_load(text)
	sources = data.get("sources") or data.get("resources") or []
	# detect list key
	if isinstance(data, list):
		sources = data
		container = None
	else:
		for key in ("sources", "resources", "admitted", "index"):
			if isinstance(data.get(key), list):
				sources = data[key]
				container = key
				break
		else:
			if "sources" in data:
				sources = data["sources"]
				container = "sources"
			else:
				raise RuntimeError("Could not find sources list in RESOURCE_INDEX.yaml")

	by_id = {s.get("id") or s.get("source_id"): s for s in sources if isinstance(s, dict)}
	updated: list[str] = []

	# Ensure src_gestalt_proximity exists as acquired entry
	if "src_gestalt_proximity" in source_ids and "src_gestalt_proximity" not in by_id:
		sources.append(
			{
				"id": "src_gestalt_proximity",
				"url": "https://www.nngroup.com/articles/proximity-principle-visual-perception/",
				"title": "Proximity Principle in Visual Perception (NN/g)",
				"author": "Nielsen Norman Group",
				"organization": "NN/g",
				"category": "visual",
				"topics": ["proximity", "gestalt_theory"],
				"credibility": 3,
				"utility": 4,
				"why_it_matters": "Practitioner mapping of Gestalt proximity to UI spacing.",
				"priority": "B",
				"status": "acquired",
				"notes": "Pass1 pipeline; preferred over OpenReplay secondary",
			}
		)
		by_id["src_gestalt_proximity"] = sources[-1]
		updated.append("src_gestalt_proximity:added")

	for sid in source_ids:
		row = by_id.get(sid)
		if not row:
			continue
		prev = row.get("status")
		row["status"] = "acquired"
		if row.get("rejection_code"):
			row.pop("rejection_code", None)
			row["notes"] = (
				(str(row.get("notes") or "") + " | Re-acquired by foropencode_pipeline").strip(" |")
			)
		if prev != "acquired":
			updated.append(f"{sid}:acquired")
		else:
			updated.append(f"{sid}:already_acquired")

	data["updated"] = date.today().isoformat()
	if container is None:
		index_path.write_text(yaml.safe_dump(sources, sort_keys=False, allow_unicode=True), encoding="utf-8")
	else:
		data[container] = sources
		index_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
	return updated
