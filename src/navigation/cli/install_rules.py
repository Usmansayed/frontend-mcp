"""Install Frontend MCP agent rules into the current working directory.

Usage:
  frontend-mcp install rules
  frontend-mcp install rules --tool cursor
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

BEGIN = "<!-- FRONTEND-MCP:BEGIN -->"
END = "<!-- FRONTEND-MCP:END -->"

CURSOR_FRONTMATTER = """\
---
description: >-
  Frontend MCP engineering partner. Apply for UI, pages, components, CSS/Tailwind,
  design, redesign, dashboards, landings, frontend bugs, forms, nav/guards,
  polish, Figma/inspiration for UI, a11y/SEO of the app, or browser verification.
alwaysApply: true
---

"""


@dataclass(frozen=True)
class AgentTool:
    key: str
    label: str
    hint: str


# Top 6 — keep stable order for the arrow picker.
AGENT_TOOLS: tuple[AgentTool, ...] = (
    AgentTool("cursor", "Cursor", ".cursor/rules/frontend-perception-mcp.mdc"),
    AgentTool("claude", "Claude Code", ".claude/rules/frontend-perception-mcp.md"),
    AgentTool("copilot", "GitHub Copilot (VS Code)", ".github/copilot-instructions.md"),
    AgentTool("opencode", "OpenCode", "AGENTS.md"),
    AgentTool("codex", "OpenAI Codex", "AGENTS.md"),
    AgentTool("windsurf", "Windsurf", ".windsurfrules"),
)


def _template_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "frontend_mcp_agent_rule.md"


def load_rule_body() -> str:
    path = _template_path()
    if not path.is_file():
        raise FileNotFoundError(f"Missing packaged rule template: {path}")
    return path.read_text(encoding="utf-8").strip() + "\n"


def _wrap_managed(body: str) -> str:
    return f"{BEGIN}\n{body.rstrip()}\n{END}\n"


def _merge_managed(existing: str, body: str) -> str:
    block = _wrap_managed(body)
    if BEGIN in existing and END in existing:
        start = existing.index(BEGIN)
        stop = existing.index(END) + len(END)
        # Drop trailing newline after END if present so we don't double-blank.
        after = existing[stop:]
        if after.startswith("\n"):
            after = after[1:]
        return existing[:start] + block + after
    existing = existing.rstrip()
    if existing:
        return existing + "\n\n" + block
    return block


def write_rules_for_tool(tool_key: str, *, root: Path | None = None) -> Path:
    """Write rule files for one tool. Returns the primary path written."""
    root = root or Path.cwd()
    body = load_rule_body()
    tool = next((t for t in AGENT_TOOLS if t.key == tool_key), None)
    if tool is None:
        known = ", ".join(t.key for t in AGENT_TOOLS)
        raise ValueError(f"Unknown tool {tool_key!r}. Choose one of: {known}")

    if tool.key == "cursor":
        path = root / ".cursor" / "rules" / "frontend-perception-mcp.mdc"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(CURSOR_FRONTMATTER + body, encoding="utf-8", newline="\n")
        return path

    if tool.key == "claude":
        path = root / ".claude" / "rules" / "frontend-perception-mcp.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="\n")
        return path

    if tool.key == "copilot":
        path = root / ".github" / "copilot-instructions.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        path.write_text(_merge_managed(existing, body), encoding="utf-8", newline="\n")
        return path

    if tool.key in ("opencode", "codex"):
        path = root / "AGENTS.md"
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        path.write_text(_merge_managed(existing, body), encoding="utf-8", newline="\n")
        return path

    if tool.key == "windsurf":
        path = root / ".windsurfrules"
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        path.write_text(_merge_managed(existing, body), encoding="utf-8", newline="\n")
        return path

    raise ValueError(f"No writer for {tool.key}")


def _stdin_is_tty() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def _read_key() -> str:
    """Return 'up' | 'down' | 'enter' | 'esc' | 'quit'."""
    if os.name == "nt":
        import msvcrt

        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x1b":
            return "esc"
        if ch in ("q", "Q"):
            return "quit"
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                return "up"
            if ch2 == "P":
                return "down"
        return "other"

    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x1b":
            # Arrow: ESC [ A/B
            rest = sys.stdin.read(2)
            if rest == "[A":
                return "up"
            if rest == "[B":
                return "down"
            return "esc"
        if ch in ("q", "Q"):
            return "quit"
        return "other"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def select_tool_interactive(tools: tuple[AgentTool, ...] = AGENT_TOOLS) -> AgentTool | None:
    """Up/down + Enter picker. Returns None if cancelled."""
    idx = 0
    n = len(tools)
    # Hide cursor while picking when possible.
    hide = "\033[?25l"
    show = "\033[?25h"
    sys.stdout.write(hide)
    sys.stdout.flush()
    try:
        while True:
            sys.stdout.write("\033[2J\033[H")  # clear screen
            sys.stdout.write("Frontend MCP — install agent rules\n")
            sys.stdout.write("Use ↑/↓ to choose, Enter to install, q to cancel\n\n")
            for i, tool in enumerate(tools):
                mark = ">" if i == idx else " "
                sys.stdout.write(f"  {mark} {tool.label}\n")
                if i == idx:
                    sys.stdout.write(f"      → {tool.hint}\n")
            sys.stdout.write("\n")
            sys.stdout.flush()

            key = _read_key()
            if key == "up":
                idx = (idx - 1) % n
            elif key == "down":
                idx = (idx + 1) % n
            elif key == "enter":
                return tools[idx]
            elif key in ("esc", "quit"):
                return None
    finally:
        sys.stdout.write(show)
        sys.stdout.flush()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="frontend-mcp install rules",
        description="Install Frontend MCP methodology rules for your AI coding agent.",
    )
    p.add_argument(
        "--tool",
        choices=[t.key for t in AGENT_TOOLS],
        help="Skip the menu and install for this tool (non-interactive).",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root (default: current directory).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = (args.root or Path.cwd()).resolve()

    if args.tool:
        tool_key = args.tool
        label = next(t.label for t in AGENT_TOOLS if t.key == tool_key)
    else:
        if not _stdin_is_tty():
            sys.stderr.write(
                "No interactive terminal. Re-run with --tool <name>, e.g.\n"
                "  frontend-mcp install rules --tool cursor\n"
                f"Options: {', '.join(t.key for t in AGENT_TOOLS)}\n"
            )
            return 2
        chosen = select_tool_interactive()
        if chosen is None:
            sys.stdout.write("Cancelled.\n")
            return 1
        tool_key = chosen.key
        label = chosen.label

    path = write_rules_for_tool(tool_key, root=root)
    rel = path.relative_to(root) if path.is_relative_to(root) else path
    sys.stdout.write(f"\n  OK  Installed Frontend MCP rules for {label}\n")
    sys.stdout.write(f"      {rel}\n")
    sys.stdout.write(f"      (in {root})\n\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
