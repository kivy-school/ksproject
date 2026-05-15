"""High-level XcodeGen/xcodebuild project orchestrator.

Mirrors ``gradle_project.GradleProject`` for the Apple side.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..pyproject_toml import PyProjectToml
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
            "build",
        ]
        result = subprocess.run(cmd, cwd=self.xcode_dir)
        if result.returncode != 0:
            raise XcodeProjectError(
                f"xcodebuild exited with code {result.returncode}"
            )
        # Locate the .app inside derivedData.
        products = derived / "Build" / "Products"
        candidates = sorted(products.rglob(f"{self.app_name}.app"))
        if not candidates:
            raise XcodeProjectError(
                f"xcodebuild succeeded but no {self.app_name}.app found under {products}"
            )
        return candidates[-1]

    def ios_build(self, variant: str = "debug", simulator: bool = False) -> Path:
        self.generate(platforms=["iOS", "macOS"])
        dest = (
            "generic/platform=iOS Simulator"
            if simulator
            else "generic/platform=iOS"
        )
        return self._xcodebuild(dest, variant)

    def macos_build(self, variant: str = "debug") -> Path:
        self.generate(platforms=["iOS", "macOS"])
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
        result = subprocess.run(
            ["xcrun", "devicectl", "list", "devices", "--json-output", "-"],
            capture_output=True, text=True,
        )
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
        ios = self.pyproject.tool.kivy_school.ios if self.pyproject.tool.kivy_school else None
        macos = self.pyproject.tool.kivy_school.macos if self.pyproject.tool.kivy_school else None
        if ios is not None:
            return ios.bundle_id
        if macos is not None:
            return macos.bundle_id
        raise XcodeProjectError("No [tool.kivy-school.ios] or [tool.kivy-school.macos] bundle_id set")

    def ios_run(
        self,
        uuid: str | None = None,
        name: str | None = None,
        variant: str = "debug",
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

        if kind == "simulator":
            subprocess.run(["xcrun", "simctl", "boot", uuid], check=False)
            app = self.ios_build(variant=variant, simulator=True)
            subprocess.run(["xcrun", "simctl", "install", uuid, str(app)], check=True)
            subprocess.run(
                ["xcrun", "simctl", "launch", uuid, self._bundle_id()], check=True
            )
        else:
            app = self.ios_build(variant=variant, simulator=False)
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

    def macos_run(self, variant: str = "debug") -> None:
        app = self.macos_build(variant=variant)
        subprocess.run(["open", "-W", str(app)], check=False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_device_by_uuid(self, uuid: str) -> dict | None:
        for d in self.devices():
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
