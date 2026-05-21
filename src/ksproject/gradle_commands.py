"""Android / Gradle CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from ksproject_utils.gradle.gradle_project import GradleProject


class GradleCommands:

    def register(self, sub: argparse._SubParsersAction) -> None:
        android = sub.add_parser("android", help="Android / Gradle commands")
        asub = android.add_subparsers(dest="command", required=True)

        p_build = asub.add_parser("build", help="Build an APK, AAR, or AAB")
        p_build.add_argument(
            "variant",
            nargs="?",
            default="debug",
            choices=["debug", "release"],
        )

        # Use a mutually exclusive group so users can't pass both --aar and --bundle
        target_type = p_build.add_mutually_exclusive_group()
        target_type.add_argument(
            "--aar",
            action="store_true",
            help="Build an AAR library instead of an APK",
        )
        target_type.add_argument(
            "--bundle",
            action="store_true",
            help="Build an AAB (Android App Bundle) instead of an APK",
        )
        p_build.set_defaults(func=self.build)

        p_devices = asub.add_parser("devices", help="List devices and AVDs")
        p_devices.set_defaults(func=self.devices)

        p_run = asub.add_parser("run", help="Build, install, and launch")
        target = p_run.add_mutually_exclusive_group(required=True)
        target.add_argument("--uuid", help="adb serial of a device or running emulator")
        target.add_argument("--name", help="AVD name to boot")
        p_run.add_argument(
            "--variant",
            default="debug",
            choices=["debug", "release"],
        )
        p_run.set_defaults(func=self.run)

    def build(self, args: argparse.Namespace) -> int:
        project = GradleProject(Path.cwd())

        output = project.build(args.variant, aar=args.aar, bundle=args.bundle)

        if args.aar:
            label = "AAR"
        elif args.bundle:
            label = "AAB"
        else:
            label = "APK"

        print(f"{label}: {output}")
        return 0

    def devices(self, args: argparse.Namespace) -> int:
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

    def run(self, args: argparse.Namespace) -> int:
        project = GradleProject(Path.cwd())
        project.run(uuid=args.uuid, name=args.name, variant=args.variant)
        return 0
