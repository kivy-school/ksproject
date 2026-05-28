"""High-level XcodeGen/xcodebuild project orchestrator.

Mirrors ``gradle_project.GradleProject`` for the Apple side.
"""
from __future__ import annotations

import json
import platform
import plistlib
import subprocess
from pathlib import Path

from ..pip_install import PipInstaller
from ..platforms import IOSArm64Platform, IOSSim_Arm64Platform, IOSSim_X86_64Platform, MacOSPlatform
from ..pyproject_toml import PyProjectToml
from .python_apple import copy_site_frameworks
from .xcode_project_builder import XcodeProjectBuilder


class XcodeProjectError(Exception):
    pass


class XcodeProject:

    builder: XcodeProjectBuilder

    def __init__(self, project_path: Path):
        project_path = Path(project_path).resolve()
        if not (project_path / "pyproject.toml").is_file():
            raise XcodeProjectError(
                f"No pyproject.toml found at {project_path}"
            )
        self.project_path = project_path
        self.pyproject = PyProjectToml(str(project_path / "pyproject.toml"))
        if self.pyproject.tool.kivy_school is None:
            raise XcodeProjectError(
                "[tool.kivy-school] section is missing in pyproject.toml"
            )
        self.builder = XcodeProjectBuilder(self.pyproject, project_path)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def app_name(self) -> str:
        return self.builder.app_name

    @property
    def xcode_dir(self) -> Path:
        return self.builder.project_dir

    @property
    def xcodeproj(self) -> Path:
        return self.xcode_dir / f"{self.app_name}.xcodeproj"

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, platforms: list[str] | None = None) -> Path:
        return self.builder.generate(platforms=platforms)

    def open_in_xcode(self) -> None:
        subprocess.run(["open", str(self.xcodeproj)], check=False)

    def install_site_packages(
        self, platforms: list[str], simulator: bool = False
    ) -> None:
        """Pip-install the project into per-platform site_packages dirs.

        After installing, move any ``.frameworks/`` dropped by the kivy wheel
        into ``Support/`` and clean them out of every site_packages slice.
        """
        platform_classes = []
        if "iOS" in platforms:
            if simulator:
                arch = platform.machine()  # 'arm64' on Apple Silicon, 'x86_64' on Intel
                if arch == "arm64":
                    platform_classes.append(IOSSim_Arm64Platform)
                else:
                    platform_classes.append(IOSSim_X86_64Platform)
            else:
                platform_classes.append(IOSArm64Platform)
        if "macOS" in platforms:
            platform_classes += [MacOSPlatform]

        for cls in platform_classes:
            plat = cls(str(self.project_path))
            Path(plat.site_packages).mkdir(parents=True, exist_ok=True)
            PipInstaller.install(
                uv_src=str(self.project_path),
                platform=plat,
                site_packages=plat.site_packages,
            )

        copy_site_frameworks(
            self.xcode_dir / "Support",
            self.xcode_dir / "site_packages",
        )

    # ------------------------------------------------------------------
    # Build via xcodebuild
    # ------------------------------------------------------------------

    @staticmethod
    def _configuration(variant: str) -> str:
        if variant == "debug":
            return "Debug"
        if variant == "release":
            return "Release"
        raise XcodeProjectError(
            f"Unknown variant {variant!r}; expected 'debug' or 'release'"
        )

    def _xcodebuild(self, destination: str, variant: str) -> Path:
        if not self.xcodeproj.exists():
            raise XcodeProjectError(
                f"Xcode project not generated yet: {self.xcodeproj} missing. "
                "Run `ksproject ios build` (or `macos build`) first."
            )
        config = self._configuration(variant)
        derived = self.xcode_dir / "build"
        cmd = [
            "xcodebuild",
            "-project", str(self.xcodeproj),
            "-scheme", self.app_name,
            "-configuration", config,
            "-destination", destination,
            "-derivedDataPath", str(derived),
            "-skipPackagePluginValidation",
            "-skipMacroValidation",
            "build",
        ]
        result = subprocess.run(cmd, cwd=self.xcode_dir, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise XcodeProjectError(
                f"xcodebuild exited with code {result.returncode}"
            )
        # Locate the .app inside derivedData.
        return self._find_app()

    def _find_app(self) -> Path:
        products = self.xcode_dir / "build" / "Build" / "Products"
        candidates = sorted(products.rglob(f"{self.app_name}.app"))
        if not candidates:
            raise XcodeProjectError(
                f"No {self.app_name}.app found under {products}. "
                "Run `ksproject ios build` first."
            )
        return candidates[-1]

    def ios_build(self, variant: str = "debug", simulator: bool = False) -> Path:
        platforms = ["iOS", "macOS"]
        just_created = not self.xcodeproj.exists()
        if just_created:
            self.generate(platforms=platforms)
            self.open_in_xcode()
        self.builder._install_frameworks(platforms)
        self.install_site_packages(platforms=["iOS"], simulator=simulator)
        self.builder.sync_site_xcframeworks()
        dest = (
            "generic/platform=iOS Simulator"
            if simulator
            else "generic/platform=iOS"
        )
        return self._xcodebuild(dest, variant)

    def macos_build(self, variant: str = "debug") -> Path:
        platforms = ["iOS", "macOS"]
        just_created = not self.xcodeproj.exists()
        if just_created:
            self.generate(platforms=platforms)
            self.open_in_xcode()
        self.builder._install_frameworks(platforms)
        self.install_site_packages(platforms=["iOS", "macOS"])
        return self._xcodebuild("generic/platform=macOS", variant)

    # ------------------------------------------------------------------
    # Devices (iOS only — simctl + devicectl)
    # ------------------------------------------------------------------

    def devices(self) -> list[dict]:
        items: list[dict] = []
        items.extend(self._list_simulators())
        items.extend(self._list_physical_devices())
        return items

    def _list_simulators(self) -> list[dict]:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "--json", "devices", "available"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        out: list[dict] = []
        for runtime, devs in (data.get("devices") or {}).items():
            for d in devs:
                out.append({
                    "kind": "simulator",
                    "uuid": d.get("udid", ""),
                    "name": d.get("name", ""),
                    "state": d.get("state", ""),
                    "runtime": runtime,
                })
        return out

    def _list_physical_devices(self) -> list[dict]:
        try:
            result = subprocess.run(
                ["xcrun", "devicectl", "list", "devices", "--json-output", "-"],
                capture_output=True, text=True, timeout=10,
            )
        except subprocess.TimeoutExpired:
            return []
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        out: list[dict] = []
        for d in (data.get("result", {}).get("devices") or []):
            ident = d.get("hardwareProperties", {}).get("udid") or d.get("identifier", "")
            name = d.get("deviceProperties", {}).get("name", "")
            out.append({
                "kind": "device",
                "uuid": ident,
                "name": name,
                "state": d.get("connectionProperties", {}).get("tunnelState", ""),
            })
        return out

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def _bundle_id(self) -> str:
        info_plist = self._find_app() / "Info.plist"
        with open(info_plist, "rb") as f:
            return plistlib.load(f)["CFBundleIdentifier"]

    def ios_run(
        self,
        uuid: str | None = None,
        name: str | None = None,
    ) -> None:
        if (uuid is None) == (name is None):
            raise XcodeProjectError("ios run requires exactly one of --uuid or --name")
        if name is not None:
            target = self._find_device_by_name(name)
            uuid = target["uuid"]
            kind = target["kind"]
        else:
            target = self._find_device_by_uuid(uuid)
            kind = target["kind"] if target else "simulator"

        app = self._find_app()
        print(f"App: {app}")
        if kind == "simulator":
            print(f"Booting simulator {uuid}...")
            subprocess.run(
                ["xcrun", "simctl", "boot", uuid],
                check=False, capture_output=True,
            )
            print(f"Installing {app.name} (this may take ~30-60s)...")
            subprocess.run(["xcrun", "simctl", "install", uuid, str(app)], check=True)
            print("Launching...")
            subprocess.run(
                ["xcrun", "simctl", "launch", "--console-pty", uuid, self._bundle_id()],
                check=True,
            )
        else:
            subprocess.run(
                ["xcrun", "devicectl", "device", "install", "app",
                 "--device", uuid, str(app)],
                check=True,
            )
            subprocess.run(
                ["xcrun", "devicectl", "device", "process", "launch",
                 "--device", uuid, self._bundle_id()],
                check=True,
            )

    def macos_run(self) -> None:
        app = self._find_app()
        subprocess.run(["open", "-W", str(app)], check=False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_device_by_uuid(self, uuid: str) -> dict | None:
        for d in self._list_simulators():
            if d["uuid"] == uuid:
                return d
        for d in self._list_physical_devices():
            if d["uuid"] == uuid:
                return d
        return None

    def _find_device_by_name(self, name: str) -> dict:
        matches = [d for d in self.devices() if d["name"] == name]
        if not matches:
            raise XcodeProjectError(f"No simulator or device named {name!r}")
        if len(matches) > 1:
            raise XcodeProjectError(
                f"Ambiguous name {name!r}; use --uuid instead"
            )
        return matches[0]
