"""CLI: python scripts/run_foropencode_pipeline.py --pass 2 --phase all"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS))

from foropencode_pipeline import gemini_client  # noqa: E402
from foropencode_pipeline.compose import compose_comparison, compose_guide  # noqa: E402
from foropencode_pipeline.extract import extract_source  # noqa: E402
from foropencode_pipeline.graph_update import upsert_edges, upsert_nodes  # noqa: E402
from foropencode_pipeline.normalize import normalize_pass  # noqa: E402
from foropencode_pipeline.paths import CONTROL, GUIDES, NORMALIZED  # noqa: E402
from foropencode_pipeline.scrape import load_pass, mark_acquired, scrape_pass  # noqa: E402
from foropencode_pipeline.validate import validate_all_cards  # noqa: E402

PASS_REQUIRED = {
	1: ["UX_HCI_STEER_011", "UX_VIS_GEST_006", "UX_HFE_TLX_001"],
	2: ["UX_HCI_KLM_008", "UX_VIS_READ_014", "UX_DS_DENS_002", "UX_DS_TOKEN_001"],
}

PASS_GUIDES = {
	1: "guide_hierarchy_density",
	2: "guide_design_systems",
}


def _log(section: str, body: str) -> None:
	log_path = CONTROL / "logs" / f"{date.today().isoformat()}.md"
	log_path.parent.mkdir(parents=True, exist_ok=True)
	prev = log_path.read_text(encoding="utf-8") if log_path.exists() else f"# {date.today().isoformat()}\n"
	block = f"\n## {section}\n\n{body.rstrip()}\n"
	if section in prev:
		# append with unique suffix when re-running
		section = f"{section} (rerun)"
		block = f"\n## {section}\n\n{body.rstrip()}\n"
	log_path.write_text(prev.rstrip() + "\n" + block, encoding="utf-8")


def phase_smoke(model: str | None) -> int:
	client = gemini_client.make_client(model=model)
	text = gemini_client.smoke_test(client, model=model)
	print(json.dumps({"smoke": "ok", "response": text, "model": model or gemini_client.DEFAULT_MODEL}))
	_log("PIPELINE - ADC smoke", f"- Model: `{model or gemini_client.DEFAULT_MODEL}`\n- Result: OK")
	return 0


def phase_scrape(pass_num: int) -> int:
	results = scrape_pass(pass_num)
	ok_ids = [r["source_id"] for r in results if r.get("ok")]
	idx = mark_acquired(ok_ids) if ok_ids else []
	print(json.dumps({"pass": pass_num, "scrape": results, "index": idx}, indent=2))
	_log(f"PIPELINE - Pass{pass_num} scrape", json.dumps(results, indent=2) + f"\n\nIndex: {idx}")
	return 0 if all(r.get("ok") for r in results) else 1


def phase_extract(pass_num: int, model: str | None) -> int:
	client = gemini_client.make_client(model=model)
	out = []
	for entry in load_pass(pass_num):
		out.append(extract_source(entry["source_id"], client=client, model=model))
	print(json.dumps(out, indent=2))
	_log(f"PIPELINE - Pass{pass_num} extract", json.dumps(out, indent=2))
	return 0 if all(r["ok"] for r in out) else 1


def phase_normalize(pass_num: int, model: str | None) -> int:
	client = gemini_client.make_client(model=model)
	out = normalize_pass(pass_num, client=client, model=model)
	print(json.dumps(out, indent=2))
	_log(f"PIPELINE - Pass{pass_num} normalize", json.dumps(out, indent=2))
	return 0 if all(r["ok"] for r in out) else 1


def phase_compose(pass_num: int, model: str | None) -> int:
	client = gemini_client.make_client(model=model)
	cmp_r = compose_comparison(pass_num, client=client, model=model)
	guide_r = compose_guide(pass_num, client=client, model=model)
	out = {"comparison": cmp_r, "guide": guide_r}
	print(json.dumps(out, indent=2))
	_log(f"PIPELINE - Pass{pass_num} compose", json.dumps(out, indent=2))
	return 0 if cmp_r["ok"] and guide_r["ok"] else 1


def phase_graph(pass_num: int) -> int:
	n = upsert_nodes(pass_num=pass_num)
	e = upsert_edges(pass_num=pass_num)
	print(json.dumps({"nodes": n, "edges": e}, indent=2))
	_log(f"PIPELINE - Pass{pass_num} graph", f"nodes={n}\nedges={e}")
	return 0


def phase_validate(pass_num: int) -> int:
	ok, total, lines = validate_all_cards()
	print("\n".join(lines))
	print(f"complete {ok}/{total}")
	_log(f"PIPELINE - Pass{pass_num} validate", f"complete {ok}/{total}\n" + "\n".join(lines))
	required = {f"{c}.json" for c in PASS_REQUIRED[pass_num]}
	failed = [ln for ln in lines if any(r in ln for r in required) and "FAIL" in ln]
	missing = [c for c in PASS_REQUIRED[pass_num] if not (NORMALIZED / f"{c}.json").exists()]
	return 0 if not failed and not missing else 1


def update_control_plane(pass_num: int, *, done: bool) -> None:
	progress = CONTROL / "PROGRESS.md"
	queue = CONTROL / "TASK_QUEUE.yaml"
	n_cards = len(list(NORMALIZED.glob("UX_*.json")))
	status = "complete" if done else "in_progress"
	p1 = ", ".join(f"`{c}`" for c in PASS_REQUIRED[1])
	p2 = ", ".join(f"`{c}`" for c in PASS_REQUIRED[2])
	progress.write_text(
		f"""# Progress (source of truth)

Last updated: {date.today().isoformat()}
Current phase: **10 - Continuous curation** (Gemini pipeline Pass{pass_num})
Active executor: **foropencode_pipeline (Cursor)**

## Phase status

| Phase | Name | Status | Gate |
|------:|------|--------|------|
| 0-9 | Spine | `complete` | Prior Cursor deep-work |
| 10 | Continuous curation | `{status}` | Pass1+Pass2 pipeline |

## Pass1 claim cards

{p1}

## Pass2 claim cards

{p2}

Normalized card count on disk: **{n_cards}**

## Guides

- `guide_hierarchy_density`
- `guide_design_systems`

## Runtime packs (v1)

- `09_runtime/pack_a11y_absolute.json`
- `09_runtime/pack_forms_checkout.json`
- `09_runtime/pack_greenfield_structure.json`

## Next action

{"Pass2 closed. Optional: runtime pack distill + more Priority B seeds / MCP wire." if done else "Finish failing Pass" + str(pass_num) + " stage; validators must pass."}
""",
		encoding="utf-8",
	)
	lines = queue.read_text(encoding="utf-8").splitlines()
	in_t010 = False
	out_lines = []
	for line in lines:
		if line.strip().startswith("id: T010"):
			in_t010 = True
		elif in_t010 and line.strip().startswith("id:"):
			in_t010 = False
		if in_t010 and line.strip().startswith("status:"):
			line = f"    status: {'done' if done else 'in_progress'}"
		out_lines.append(line)
	queue.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description="ForOpenCode Gemini corpus pipeline")
	parser.add_argument(
		"--phase",
		required=True,
		choices=[
			"smoke",
			"scrape",
			"extract",
			"normalize",
			"compose",
			"graph",
			"validate",
			"control",
			"all",
		],
	)
	parser.add_argument("--pass", dest="pass_num", type=int, default=1, choices=[1, 2])
	parser.add_argument("--model", default=None, help="Override FOROPENCODE_GEMINI_MODEL")
	args = parser.parse_args(argv)
	model = args.model
	pass_num = args.pass_num

	if args.phase == "smoke":
		return phase_smoke(model)
	if args.phase == "scrape":
		return phase_scrape(pass_num)
	if args.phase == "extract":
		return phase_extract(pass_num, model)
	if args.phase == "normalize":
		return phase_normalize(pass_num, model)
	if args.phase == "compose":
		return phase_compose(pass_num, model)
	if args.phase == "graph":
		return phase_graph(pass_num)
	if args.phase == "validate":
		code = phase_validate(pass_num)
		update_control_plane(pass_num, done=(code == 0))
		return code
	if args.phase == "control":
		required = PASS_REQUIRED[pass_num]
		guide = PASS_GUIDES[pass_num]
		done = all((NORMALIZED / f"{c}.json").exists() for c in required) and (
			GUIDES / f"{guide}.json"
		).exists()
		if done:
			code = phase_validate(pass_num)
			done = code == 0
		ok, total, _ = validate_all_cards()
		update_control_plane(pass_num, done=done)
		print(json.dumps({"done": done, "cards_ok": ok, "cards_total": total, "pass": pass_num}))
		return 0 if done else 1

	for phase in ("scrape", "extract", "normalize", "compose", "graph", "validate"):
		print(f"\n=== PASS{pass_num} PHASE {phase} ===", flush=True)
		fn = {
			"scrape": lambda: phase_scrape(pass_num),
			"extract": lambda: phase_extract(pass_num, model),
			"normalize": lambda: phase_normalize(pass_num, model),
			"compose": lambda: phase_compose(pass_num, model),
			"graph": lambda: phase_graph(pass_num),
			"validate": lambda: phase_validate(pass_num),
		}[phase]
		code = fn()
		if code != 0:
			update_control_plane(pass_num, done=False)
			print(f"STOP at phase {phase} exit={code}", flush=True)
			return code
	update_control_plane(pass_num, done=True)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
