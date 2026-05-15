"""ksproject CLI entrypoint."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ksproject_utils.gradle.gradle_project import GradleProject
from ksproject_utils.project_init import ProjectInit
from ksproject_utils.xcode.xcode_project import XcodeProject


class KSProjectCLI:

    def __init__(self) -> None:
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

        android = sub.add_parser("android", help="Android / Gradle commands")
        asub = android.add_subparsers(dest="command", required=True)

        p_build = asub.add_parser("build", help="Build an APK")
        p_build.add_argument(
            "variant",
            nargs="?",
            default="debug",
            choices=["debug", "release"],
        )
        p_build.add_argument(
            "--aar",
            action="store_true",
            help="Build an AAR library instead of an APK",
        )
        p_build.set_defaults(func=self.android_build)

        p_devices = asub.add_parser("devices", help="List devices and AVDs")
        p_devices.set_defaults(func=self.android_devices)

        p_run = asub.add_parser("run", help="Build, install, and launch")
        target = p_run.add_mutually_exclusive_group(required=True)
        target.add_argument(
            "--uuid", help="adb serial of a device or running emulator"
        )
        target.add_argument("--name", help="AVD name to boot")
        p_run.add_argument(
            "--variant",
            default="debug",
            choices=["debug", "release"],
        )
        p_run.set_defaults(func=self.android_run)

        # ---- ios ----
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
            "--simulator",
            action="store_true",
            help="Build for iOS Simulator instead of device",
        )
        ip_build.set_defaults(func=self.ios_build)

        ip_devices = isub.add_parser(
            "devices", help="List iOS simulators and connected devices"
        )
        ip_devices.set_defaults(func=self.ios_devices)

        ip_run = isub.add_parser("run", help="Build, install, and launch on iOS")
        itarget = ip_run.add_mutually_exclusive_group(required=True)
        itarget.add_argument("--uuid", help="UDID of a simulator or device")
        itarget.add_argument("--name", help="Simulator/device name")
        ip_run.add_argument(
            "--variant",
            default="debug",
            choices=["debug", "release"],
        )
        ip_run.set_defaults(func=self.ios_run)

        # ---- macos ----
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

        mp_run = msub.add_parser("run", help="Build and launch on macOS")
        mp_run.add_argument(
            "--variant",
            default="debug",
            choices=["debug", "release"],
        )
        mp_run.set_defaults(func=self.macos_run)

        return parser

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def init(self, args: argparse.Namespace) -> int:
        ProjectInit(Path(args.path), app_name=args.name).run()
        return 0

    def android_build(self, args: argparse.Namespace) -> int:
        project = GradleProject(Path.cwd())
        output = project.build(args.variant, aar=args.aar)
        label = "AAR" if args.aar else "APK"
        print(f"{label}: {output}")
        return 0

    def android_devices(self, args: argparse.Namespace) -> int:
        project = GradleProject(Path.cwd())
        items = project.devices()
        if not items:
            print("(no devices or AVDs found)")
            return 0
        for it in items:
            if it.get("kind") == "device":
                print(
                    f"device  serial={it['serial']:<20} state={it['state']:<12}"
                    f" model={it.get('model', '')}"
                )
            else:
                print(f"avd     name={it['name']}")
        return 0

    def android_run(self, args: argparse.Namespace) -> int:
        project = GradleProject(Path.cwd())
        project.run(uuid=args.uuid, name=args.name, variant=args.variant)
        return 0

    # ---- ios ----

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
        project.ios_run(uuid=args.uuid, name=args.name, variant=args.variant)
        return 0

    # ---- macos ----

    def macos_build(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        app = project.macos_build(variant=args.variant)
        print(f"app: {app}")
        return 0

    def macos_run(self, args: argparse.Namespace) -> int:
        project = XcodeProject(Path.cwd())
        project.macos_run(variant=args.variant)
        return 0

    # ------------------------------------------------------------------
    # Entrypoint
    # ------------------------------------------------------------------

    def run(self, argv: list[str] | None = None) -> int:
        args = self.parser.parse_args(argv)
        return args.func(args) or 0


def main() -> None:
    sys.exit(KSProjectCLI().run())
