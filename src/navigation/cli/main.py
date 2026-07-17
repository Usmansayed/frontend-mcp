"""CLI entry: serve MCP by default, or `install rules` for agent rule setup."""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] == "install":
        rest = args[1:]
        if rest and rest[0] == "rules":
            from navigation.cli.install_rules import main as rules_main

            raise SystemExit(rules_main(rest[1:]))
        sys.stderr.write(
            "Usage:\n"
            "  frontend-mcp install rules     Install agent rules (interactive)\n"
            "  frontend-mcp-install            Install/upgrade the MCP package from PyPI\n"
            "  frontend-mcp                    Start the MCP server (default)\n"
        )
        raise SystemExit(2)

    # Default: MCP stdio server (Cursor / host launches with no subcommand).
    from navigation.mcp.server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
