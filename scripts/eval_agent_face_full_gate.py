"""One-shot gate for agent-face + coordination regression boards.

Exit 0 only if every board passes.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, cmd: list[str]) -> bool:
	print(f"\n======== {label} ========", flush=True)
	env = {**dict(**__import__("os").environ), "PYTHONPATH": str(ROOT / "src")}
	p = subprocess.run(cmd, cwd=str(ROOT), env=env)
	ok = p.returncode == 0
	print(f"======== {label}: {'PASS' if ok else 'FAIL'} ========", flush=True)
	return ok


def main() -> int:
	py = sys.executable
	boards = [
		("unit_card", [py, "-m", "pytest", "tests/test_coordinator_card.py", "-q", "--tb=line"]),
		("decision_lab_baseline", [py, "-m", "pytest", "tests/decision_lab/test_exp023_episode_card.py", "-q", "--tb=line"]),
		("hard_matrix", [py, "scripts/eval_agent_face_hard_matrix.py"]),
		("obedience", [py, "scripts/eval_agent_face_phase2_obedience.py"]),
		("discoverability", [py, "scripts/eval_agent_face_discoverability.py"]),
		("done_ladder", [py, "scripts/hard_done_ladder_sim.py"]),
		("phase3", [py, "-u", "scripts/eval_agent_face_phase3_reliability.py"]),
		(
			"no_guide_e2e",
			[
				py,
				"-u",
				"scripts/eval_agent_face_no_guide_e2e.py",
				"--cases",
				"forms,hotfix,greenfield,redesign,feature,polish,hotfix_stamped_feature,landing_signup_not_forms,checkout_feature_not_forms",
			],
		),
	]
	failed: list[str] = []
	for label, cmd in boards:
		if not run(label, cmd):
			failed.append(label)
	print("\n================ SUMMARY ================")
	if failed:
		print("FAIL:", ", ".join(failed))
		return 1
	print("ALL BOARDS PASS")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
