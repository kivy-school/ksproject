"""Android / Gradle CLI commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ksproject_utils.gradle.android_toolchain import AndroidToolchain
from ksproject_utils.gradle.gradle_project import GradleProject
from ksproject_utils.pyproject_toml import PyProjectToml


class GradleCommands:

    def register(self, sub: argparse._SubParsersAction) -> None:
        android = sub.add_parser("android", help="Android / Gradle commands")
        asub = android.add_subparsers(dest="command", required=True)

        # --- BUILD ---
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

        p_build.add_argument(
            "--clean",
            action="store_true",
            help="Perform a clean build",
        )
        p_build.set_defaults(func=self.build)

        # --- SIGN ---
        p_sign = asub.add_parser(
            "sign", help="Sign automatically discovered project artifacts"
        )
        p_sign.add_argument(
            "--keystore", type=Path, required=True, help="Path to keystore file"
        )
        p_sign.add_argument(
            "--storepass", type=str, required=True, help="Keystore password"
        )
        p_sign.add_argument(
            "--keyalias", type=str, required=True, help="Key alias identifier"
        )
        p_sign.add_argument(
            "--keypass", type=str, help="Alias key password (if different)"
        )
        p_sign.add_argument(
            "--variant",
            default="release",
            choices=["debug", "release"],
            help="Target variant directory to look inside (defaults to release)",
        )

        sign_target = p_sign.add_mutually_exclusive_group()
        sign_target.add_argument(
            "--bundle",
            action="store_true",
            help="Look for and sign the App Bundle (.aab)",
        )
        sign_target.add_argument(
            "--apk",
            action="store_true",
            default=True,
            help="Look for and sign the APK (Default)",
        )

        p_sign.set_defaults(func=self.sign)

        # --- GENKEY ---
        p_genkey = asub.add_parser(
            "genkey", help="Generate a new release keystore signature file"
        )
        p_genkey.add_argument(
            "--out",
            type=Path,
            required=True,
            help="Output destination path for the keystore",
        )
        p_genkey.add_argument(
            "--storepass",
            type=str,
            required=True,
            help="Keystore storage access password",
        )
        p_genkey.add_argument(
            "--keyalias", type=str, required=True, help="Alias profile handle string"
        )
        p_genkey.add_argument(
            "--keypass", type=str, help="Alias key password (defaults to storepass)"
        )
        p_genkey.add_argument(
            "--dname",
            type=str,
            help="Distinguished Name string (e.g., 'CN=App, O=Org')",
        )

        p_genkey.set_defaults(func=self.genkey)

        # --- GET-PATH ---
        p_get_path = asub.add_parser(
            "get-path", help="Print the resolved path for a tool"
        )
        p_get_path.add_argument("tool", choices=["sdk", "ndk", "emulator"])
        p_get_path.set_defaults(func=self.get_path)

        # --- DEVICES ---
        p_devices = asub.add_parser("devices", help="List devices and AVDs")
        p_devices.set_defaults(func=self.devices)

        # --- RUN ---
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

    def get_path(self, args: argparse.Namespace) -> int:
        pyproject = PyProjectToml(str(Path.cwd() / "pyproject.toml"))
        android = (
            pyproject.tool.kivy_school.android if pyproject.tool.kivy_school else None
        )

        if args.tool == "sdk":
            path = AndroidToolchain.find_sdk_path(android, Path.cwd())
        elif args.tool == "ndk":
            path = AndroidToolchain.find_ndk_path(android, Path.cwd())
        else:  # emulator
            sdk = AndroidToolchain.find_sdk_path(android, Path.cwd())
            if sdk is None:
                path = None
            else:
                exe_suffix = ".exe" if sys.platform == "win32" else ""
                emu = Path(sdk) / "emulator" / f"emulator{exe_suffix}"
                path = str(emu) if emu.exists() else None

        if path is None:
            print(f"{args.tool} not found", file=sys.stderr)
            return 1
        print(path)
        return 0

    def build(self, args: argparse.Namespace) -> int:
        project = GradleProject(Path.cwd())

        output = project.build(
            args.variant, aar=args.aar, bundle=args.bundle, clean=args.clean
        )

        if args.aar:
            label = "AAR"
        elif args.bundle:
            label = "AAB"
        else:
            label = "APK"

        print(f"{label}: {output}")
        return 0

    def sign(self, args: argparse.Namespace) -> int:
        project = GradleProject(Path.cwd())

        output = project.sign_project_artifact(
            keystore=args.keystore,
            storepass=args.storepass,
            keyalias=args.keyalias,
            keypass=args.keypass,
            variant=args.variant,
            bundle=args.bundle,
        )

        label = "AAB" if args.bundle else "APK"
        print(f"Signed {label}: {output}")
        return 0

    def genkey(self, args: argparse.Namespace) -> int:
        project = GradleProject(Path.cwd())

        output = project.genkey(
            keystore_path=args.out,
            storepass=args.storepass,
            keyalias=args.keyalias,
            keypass=args.keypass,
            dname=args.dname,
        )

        print(f"Keystore generated: {output}")
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
