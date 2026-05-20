"""ksproject CLI entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ksproject_utils.project_init import ProjectInit

from ksproject.apple_commands import AppleCommands
from ksproject.gradle_commands import GradleCommands


class KSProjectCLI:

    def __init__(self) -> None:
        self._gradle = GradleCommands()
        self._apple = AppleCommands()
        self.parser = self._build_parser()

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="ksproject")
        sub = parser.add_subparsers(dest="subsystem", required=True)

        p_init = sub.add_parser("init", help="Initialize a new ksproject")
        p_init.add_argument(
            "path",
            nargs="?",
            default=".",
            help="Project directory (default: current directory)",
        )
        p_init.add_argument("--name", help="App name (default: directory name)")
        p_init.set_defaults(func=self.init)

        self._gradle.register(sub)
        self._apple.register(sub)

        return parser

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def init(self, args: argparse.Namespace) -> int:
        ProjectInit(Path(args.path), app_name=args.name).run()
        return 0

    # ------------------------------------------------------------------
    # Entrypoint
    # ------------------------------------------------------------------

    def run(self, argv: list[str] | None = None) -> int:
        args = self.parser.parse_args(argv)
        return args.func(args) or 0


def main() -> None:
    sys.exit(KSProjectCLI().run())
