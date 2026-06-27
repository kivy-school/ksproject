"""iOS / macOS / Xcode CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from ksproject_utils.xcode.xcode_project import XcodeProject


class AppleCommands:

    def register(self, sub: argparse._SubParsersAction) -> None:
        self._register_ios(sub)
        self._register_ios_sim(sub)
        self._register_macos(sub)

    def _register_ios(self, sub: argparse._SubParsersAction) -> None:
        ios = sub.add_parser("ios", help="iOS device commands")
        isub = ios.add_subparsers(dest="command", required=True)

        ip_build = isub.add_parser("build", help="Build an .app for iOS device")
        ip_build.add_argument(
            "variant",
            nargs="?",
            default="debug",
            choices=["debug", "release"],
        )
        ip_build.set_defaults(func=self.ios_build)

        ip_devices = isub.add_parser(
            "devices", help="List iOS simulators and connected devices"
        )
        ip_devices.set_defaults(func=self.ios_devices)

        ip_run = isub.add_parser(
            "run", help="Install and launch on a device"
        )
        itarget = ip_run.add_mutually_exclusive_group(required=True)
        itarget.add_argument("--uuid", help="UDID of a device")
        itarget.add_argument("--name", help="Device name")
        ip_run.set_defaults(func=self.ios_run)

        ip_open = isub.add_parser("open", help="Open the Xcode project in Xcode")
        ip_open.set_defaults(func=self.ios_open)

    def _register_ios_sim(self, sub: argparse._SubParsersAction) -> None:
        ios_sim = sub.add_parser("ios-sim", help="iOS Simulator commands")
        ssub = ios_sim.add_subparsers(dest="command", required=True)

        sp_build = ssub.add_parser("build", help="Build an .app for iOS Simulator")
        sp_build.add_argument(
            "variant",
            nargs="?",
            default="debug",
            choices=["debug", "release"],
        )
        sp_build.set_defaults(func=self.ios_sim_build)

        sp_devices = ssub.add_parser("devices", help="List available iOS simulators")
        sp_devices.set_defaults(func=self.ios_sim_devices)

        sp_run = ssub.add_parser(
            "run", help="Install and launch on a simulator"
        )
        starget = sp_run.add_mutually_exclusive_group(required=True)
        starget.add_argument("--uuid", help="UDID of a simulator")
        starget.add_argument("--name", help="Simulator name")
        sp_run.set_defaults(func=self.ios_run)

        sp_open = ssub.add_parser("open", help="Open the Xcode project in Xcode")
        sp_open.set_defaults(func=self.ios_open)

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

        mp_open = msub.add_parser("open", help="Open the Xcode project in Xcode")
        mp_open.set_defaults(func=self.macos_open)

    def ios_build(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        app = project.ios_build(variant=args.variant, simulator=False)
        print(f"app: {app}")
        return 0

    def ios_sim_build(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        app = project.ios_build(variant=args.variant, simulator=True)
        print(f"app: {app}")
        return 0

    def ios_devices(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        items = [d for d in project.devices() if d["kind"] == "device"]
        if not items:
            print("(no connected iOS devices found)")
            return 0
        for it in items:
            print(
                f"{it['kind']:<10} uuid={it['uuid']:<40} "
                f"state={it.get('state', ''):<12} name={it.get('name', '')}"
            )
        return 0

    def ios_sim_devices(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        items = [d for d in project.devices() if d["kind"] == "simulator"]
        if not items:
            print("(no iOS simulators found)")
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

    def ios_open(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        project.open_in_xcode()
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

    def macos_open(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        project.open_in_xcode()
        return 0
