"""iOS / macOS / Xcode CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from ksproject_utils.xcode.xcode_project import XcodeProject


class AppleCommands:

    def register(self, sub: argparse._SubParsersAction) -> None:
        self._register_ios(sub)
        self._register_macos(sub)

    def _register_ios(self, sub: argparse._SubParsersAction) -> None:
        ios = sub.add_parser("ios", help="iOS / Xcode commands")
        isub = ios.add_subparsers(dest="command", required=True)

        ip_build = isub.add_parser("build", help="Build an .app for iOS")
        ip_build.add_argument(
            "variant",
            nargs="?",
            default="debug",
            choices=["debug", "release"],
        )
        ip_build.add_argument(
            "--sim",
            action="store_true",
            dest="simulator",
            help="Build for iOS Simulator instead of device",
        )
        ip_build.set_defaults(func=self.ios_build)

        ip_devices = isub.add_parser(
            "devices", help="List iOS simulators and connected devices"
        )
        ip_devices.set_defaults(func=self.ios_devices)

        ip_run = isub.add_parser(
            "run", help="Install and launch on a simulator or device"
        )
        itarget = ip_run.add_mutually_exclusive_group(required=True)
        itarget.add_argument("--uuid", help="UDID of a simulator or device")
        itarget.add_argument("--name", help="Simulator/device name")
        ip_run.set_defaults(func=self.ios_run)

    def _register_macos(self, sub: argparse._SubParsersAction) -> None:
        macos = sub.add_parser("macos", help="macOS / Xcode commands")
        msub = macos.add_subparsers(dest="command", required=True)

        mp_build = msub.add_parser("build", help="Build an .app for macOS")
        mp_build.add_argument(
            "variant",
            nargs="?",
            default="debug",
            choices=["debug", "release"],
        )
        mp_build.set_defaults(func=self.macos_build)

        mp_run = msub.add_parser("run", help="Launch the built .app on macOS")
        mp_run.set_defaults(func=self.macos_run)

    def ios_build(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        app = project.ios_build(variant=args.variant, simulator=args.simulator)
        print(f"app: {app}")
        return 0

    def ios_devices(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        items = project.devices()
        if not items:
            print("(no iOS devices or simulators found)")
            return 0
        for it in items:
            print(
                f"{it['kind']:<10} uuid={it['uuid']:<40} "
                f"state={it.get('state', ''):<12} name={it.get('name', '')}"
            )
        return 0

    def ios_run(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        project.ios_run(uuid=args.uuid, name=args.name)
        return 0

    def macos_build(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        app = project.macos_build(variant=args.variant)
        print(f"app: {app}")
        return 0

    def macos_run(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        project.macos_run()
        return 0
