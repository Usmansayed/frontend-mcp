"""frontend-mcp setup — validate install, print mcp.json, optional Cursor skill.

No silent mutations of user repos. Opt-in flags only for skill install.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _pkg_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _which_frontend_mcp() -> str | None:
    return shutil.which("frontend-mcp") or shutil.which("frontend-mcp.exe")


def _skill_template_dir() -> Path:
    return (
        Path(__file__).resolve().parent
        / "data"
        / "skills"
        / "frontend-engineering-with-perception"
    )


def install_cursor_skill(*, dest_root: Path | None = None) -> Path:
    """Copy packaged skill into ~/.cursor/skills/ (or dest_root)."""
    src = _skill_template_dir()
    if not (src / "SKILL.md").is_file():
        raise FileNotFoundError(f"Missing packaged skill: {src / 'SKILL.md'}")
    root = dest_root or (Path.home() / ".cursor" / "skills")
    dest = root / "frontend-engineering-with-perception"
    dest.mkdir(parents=True, exist_ok=True)
    for path in src.rglob("*"):
        if path.is_file():
            rel = path.relative_to(src)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    return dest


def cursor_rule_snippet() -> str:
    return (
        "Copy into .cursor/rules/frontend-perception-mcp.mdc only if you want an "
        "always-on project rule. Prefer:\n"
        "  frontend-mcp install rules --tool cursor\n"
        "Or keep the short packaged rule from the PyPI package without auto-writing."
    )


def agents_md_template() -> str:
    return """# Frontend MCP (optional repo note)

For UI / frontend / visual tasks in this repo:

1. `perception_health({ url, intent })` with the real task
2. `perception_session_start({ base_url, intent })`
3. Read `agent_summary.coordinator` / `recommended_next` before scaffolding pages
4. Verify with `data.verified=true` before claiming done

Do not treat this file as a tool catalog — see `perception://getting-started`.
"""


def print_setup_report(*, install_skill: bool, print_rule: bool, print_agents: bool) -> int:
    from navigation.core.package_meta import installed_version

    engine = installed_version(default="") or None
    if engine in {"", "0.0.0"}:
        engine = _pkg_version("frontend-mcp") or _pkg_version("frontend-perception-engine")
    exe = _which_frontend_mcp()

    sys.stdout.write("Frontend MCP — setup\n")
    sys.stdout.write("====================\n\n")
    sys.stdout.write(f"  frontend-mcp: {engine or 'NOT INSTALLED'}\n")
    sys.stdout.write(f"  frontend-mcp on PATH:       {exe or 'NOT FOUND'}\n\n")

    if not engine:
        sys.stdout.write(
            "Install first:\n"
            "  pip install frontend-mcp\n"
            "  # or: uvx --from frontend-mcp frontend-mcp-install\n\n"
        )
        return 1

    mcp_block = {
        "mcpServers": {
            "frontend-mcp": {
                "command": "frontend-mcp",
                "args": [],
            }
        }
    }
    sys.stdout.write("Add to Cursor MCP settings (mcp.json):\n\n")
    sys.stdout.write(json.dumps(mcp_block, indent=2))
    sys.stdout.write("\n\n")

    sys.stdout.write("3-line workflow:\n")
    sys.stdout.write("  1. session_start with intent\n")
    sys.stdout.write("  2. read agent_summary.coordinator / recommended_next\n")
    sys.stdout.write("  3. verify (data.verified=true) before claim-done\n\n")

    if install_skill:
        dest = install_cursor_skill()
        sys.stdout.write(f"Installed Cursor skill → {dest}\n")
        sys.stdout.write("  Restart Cursor or reload skills if it does not appear.\n\n")
    else:
        sys.stdout.write(
            "Optional: install the Frontend Engineering methodology skill:\n"
            "  frontend-mcp setup --cursor-skill\n\n"
        )

    if print_rule:
        sys.stdout.write("--- Cursor rule (print only; not written) ---\n")
        sys.stdout.write(cursor_rule_snippet())
        sys.stdout.write("\n\n")

    if print_agents:
        sys.stdout.write("--- AGENTS.md template (print only; not written) ---\n")
        sys.stdout.write(agents_md_template())
        sys.stdout.write("\n")

    sys.stdout.write(
        "Health smoke: start your app, then in the agent call "
        "perception_health({ url, intent }).\n"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="frontend-mcp setup",
        description=(
            "Validate Frontend MCP install, print mcp.json, optional --cursor-skill. "
            "Does not mutate repo files unless you opt in to skill install."
        ),
    )
    parser.add_argument(
        "--cursor-skill",
        action="store_true",
        help="Install personal skill to ~/.cursor/skills/frontend-engineering-with-perception/",
    )
    parser.add_argument(
        "--cursor-rule",
        action="store_true",
        help="Print Cursor rule install hint (does not write files).",
    )
    parser.add_argument(
        "--agents-md",
        action="store_true",
        help="Print AGENTS.md template (does not write files).",
    )
    args = parser.parse_args(argv)
    return print_setup_report(
        install_skill=bool(args.cursor_skill),
        print_rule=bool(args.cursor_rule),
        print_agents=bool(args.agents_md),
    )


if __name__ == "__main__":
    raise SystemExit(main())
