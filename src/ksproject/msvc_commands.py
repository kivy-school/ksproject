"""Windows / MSVC CLI commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ksproject_utils.msvc.msvc_project import MsvcProject


class MsvcCommands:

    def register(self, sub: argparse._SubParsersAction) -> None:
        windows = sub.add_parser("windows", help="Windows / MSVC commands")
        wsub = windows.add_subparsers(dest="command", required=True)

        # --- BUILD ---
        p_build = wsub.add_parser("build", help="Build a Windows executable (.exe)")
        p_build.add_argument(
            "variant",
            nargs="?",
            default="release",
            choices=["debug", "release"],
            help="Target variant (debug keeps console open, release hides it)",
        )
        p_build.add_argument(
            "--clean",
            action="store_true",
            help="Perform a clean build",
        )
        p_build.set_defaults(func=self.build)

        # --- RUN ---
        p_run = wsub.add_parser("run", help="Launch the compiled Windows executable")
        p_run.set_defaults(func=self.run)

    def build(self, args: argparse.Namespace) -> int:
        try:
            project = MsvcProject(Path.cwd())
            output = project.build(variant=args.variant, clean=args.clean)
            print(f"EXECUTABLE at: {output}")
            return 0
        except Exception as e:
            print(f"Error building Windows project: {e}", file=sys.stderr)
            return 1

    def run(self, args: argparse.Namespace) -> int:
        try:
            project = MsvcProject(Path.cwd())
            project.run()
            return 0
        except Exception as e:
            print(f"Error running Windows project: {e}", file=sys.stderr)
            return 1
