"""iOS / macOS / Xcode CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from ksproject_utils.xcode.xcode_project import XcodeProject


def _project() -> XcodeProject:
    return XcodeProject(Path.cwd())


def _add_variant(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "variant",
        nargs="?",
        default="debug",
        choices=["debug", "release"],
    )


def _add_archive(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "variant",
        nargs="?",
        default="release",
        choices=["debug", "release"],
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload the archive to App Store Connect after archiving",
    )
    parser.add_argument(
        "--asc-key-id",
        help="App Store Connect API Key ID (falls back to env ASC_KEY_ID)",
    )
    parser.add_argument(
        "--asc-issuer-id",
        help="App Store Connect API Issuer ID (falls back to env ASC_ISSUER_ID)",
    )
    parser.add_argument(
        "--asc-key-path",
        help="Path to the .p8 API key file (falls back to env ASC_KEY_PATH)",
    )
    parser.add_argument(
        "--build-number",
        help="Stamp CFBundleVersion before archiving (e.g. CI run number)",
    )
    parser.add_argument(
        "--app-version",
        help="Stamp CFBundleShortVersionString before archiving (e.g. tag 1.2.3)",
    )


def _print_devices(items: list[dict], empty_msg: str) -> None:
    if not items:
        print(empty_msg)
        return
    for it in items:
        print(
            f"{it['kind']:<10} uuid={it['uuid']:<40} "
            f"state={it.get('state', ''):<12} name={it.get('name', '')}"
        )


class AppleCommands:

    def __init__(self) -> None:
        self.ios = self.IosCommands()
        self.sim = self.SimCommands()
        self.macos = self.MacosCommands()
        self.xcode = self.XcodeCommands()

    def register(self, sub: argparse._SubParsersAction) -> None:
        apple = sub.add_parser("apple", help="Apple platform commands (iOS / macOS)")
        psub = apple.add_subparsers(dest="platform", required=True)
        self.ios.register(psub)
        self.sim.register(psub)
        self.macos.register(psub)
        self.xcode.register(psub)
        self._register_all(psub)

    def _register_all(self, sub: argparse._SubParsersAction) -> None:
        allp = sub.add_parser("all", help="Run across all Apple platforms")
        asub = allp.add_subparsers(dest="command", required=True)

        ap_build = asub.add_parser(
            "build", help="Build for iOS device, iOS Simulator and macOS"
        )
        _add_variant(ap_build)
        ap_build.set_defaults(func=self.all_build)

    def all_build(self, args: argparse.Namespace) -> int:
        self.ios.build(args)
        self.sim.build(args)
        self.macos.build(args)
        return 0

    class IosCommands:

        def register(self, sub: argparse._SubParsersAction) -> None:
            ios = sub.add_parser("ios", help="iOS device commands")
            isub = ios.add_subparsers(dest="command", required=True)

            build = isub.add_parser("build", help="Build an .app for iOS device")
            _add_variant(build)
            build.set_defaults(func=self.build)

            archive = isub.add_parser(
                "archive", help="Archive for distribution (App Store)"
            )
            _add_archive(archive)
            archive.set_defaults(func=self.archive)

            action = isub.add_parser(
                "create-action",
                help="Create a tag-triggered GitHub Actions App Store workflow",
            )
            action.set_defaults(func=self.create_action)

            devices = isub.add_parser(
                "devices", help="List iOS simulators and connected devices"
            )
            devices.set_defaults(func=self.devices)

            run = isub.add_parser("run", help="Install and launch on a device")
            target = run.add_mutually_exclusive_group(required=True)
            target.add_argument("--uuid", help="UDID of a device")
            target.add_argument("--name", help="Device name")
            run.set_defaults(func=self.run)

        def build(self, args: argparse.Namespace) -> int:
            app = _project().ios_build(variant=args.variant, simulator=False)
            print(f"app: {app}")
            return 0

        def archive(self, args: argparse.Namespace) -> int:
            archive = _project().ios_archive(
                variant=args.variant,
                upload=args.upload,
                key_id=args.asc_key_id,
                issuer_id=args.asc_issuer_id,
                key_path=args.asc_key_path,
                build_number=args.build_number,
                app_version=args.app_version,
            )
            print(f"archive: {archive}")
            return 0

        def create_action(self, args: argparse.Namespace) -> int:
            workflow = _project().create_action("ios")
            print(f"workflow: {workflow}")
            return 0

        def devices(self, args: argparse.Namespace) -> int:
            items = [d for d in _project().devices() if d["kind"] == "device"]
            _print_devices(items, "(no connected iOS devices found)")
            return 0

        def run(self, args: argparse.Namespace) -> int:
            _project().ios_run(uuid=args.uuid, name=args.name)
            return 0

    class SimCommands:

        def register(self, sub: argparse._SubParsersAction) -> None:
            sim = sub.add_parser("sim", help="iOS Simulator commands")
            ssub = sim.add_subparsers(dest="command", required=True)

            build = ssub.add_parser("build", help="Build an .app for iOS Simulator")
            _add_variant(build)
            build.set_defaults(func=self.build)

            devices = ssub.add_parser("devices", help="List available iOS simulators")
            devices.set_defaults(func=self.devices)

            run = ssub.add_parser("run", help="Install and launch on a simulator")
            target = run.add_mutually_exclusive_group(required=True)
            target.add_argument("--uuid", help="UDID of a simulator")
            target.add_argument("--name", help="Simulator name")
            run.set_defaults(func=self.run)

        def build(self, args: argparse.Namespace) -> int:
            app = _project().ios_build(variant=args.variant, simulator=True)
            print(f"app: {app}")
            return 0

        def devices(self, args: argparse.Namespace) -> int:
            items = [d for d in _project().devices() if d["kind"] == "simulator"]
            _print_devices(items, "(no iOS simulators found)")
            return 0

        def run(self, args: argparse.Namespace) -> int:
            _project().ios_run(uuid=args.uuid, name=args.name)
            return 0

    class MacosCommands:

        def register(self, sub: argparse._SubParsersAction) -> None:
            macos = sub.add_parser("macos", help="macOS / Xcode commands")
            msub = macos.add_subparsers(dest="command", required=True)

            build = msub.add_parser("build", help="Build an .app for macOS")
            _add_variant(build)
            build.set_defaults(func=self.build)

            archive = msub.add_parser(
                "archive", help="Archive for distribution (App Store)"
            )
            _add_archive(archive)
            archive.set_defaults(func=self.archive)

            action = msub.add_parser(
                "create-action",
                help="Create a tag-triggered GitHub Actions App Store workflow",
            )
            action.set_defaults(func=self.create_action)

            run = msub.add_parser("run", help="Launch the built .app on macOS")
            run.set_defaults(func=self.run)

        def build(self, args: argparse.Namespace) -> int:
            app = _project().macos_build(variant=args.variant)
            print(f"app: {app}")
            return 0

        def archive(self, args: argparse.Namespace) -> int:
            archive = _project().macos_archive(
                variant=args.variant,
                upload=args.upload,
                key_id=args.asc_key_id,
                issuer_id=args.asc_issuer_id,
                key_path=args.asc_key_path,
                build_number=args.build_number,
                app_version=args.app_version,
            )
            print(f"archive: {archive}")
            return 0

        def create_action(self, args: argparse.Namespace) -> int:
            workflow = _project().create_action("macos")
            print(f"workflow: {workflow}")
            return 0

        def run(self, args: argparse.Namespace) -> int:
            _project().macos_run()
            return 0

    class XcodeCommands:

        def register(self, sub: argparse._SubParsersAction) -> None:
            xcode = sub.add_parser("xcode", help="Xcode project commands")
            xsub = xcode.add_subparsers(dest="command", required=True)

            open_p = xsub.add_parser("open", help="Open the Xcode project in Xcode")
            open_p.set_defaults(func=self.open)

        def open(self, args: argparse.Namespace) -> int:
            _project().open_in_xcode()
            return 0
