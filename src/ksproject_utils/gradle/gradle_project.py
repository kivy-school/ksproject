"""High-level Gradle/Android project orchestrator.

Single entrypoint used by both CLI and GUI: instantiate with a project path,
then call `build()`, `devices()`, or `run()`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..pip_install import PipInstaller
from ..platforms import (
    AndroidArm64Platform,
    AndroidPlatform,
    AndroidX86_64Platform,
)
from ..pyproject_toml import KivySchoolData, PyProjectToml
from .adb import ADB
from .android_emulator import AndroidEmulator
from .android_toolchain import DEFAULT_API_VERSION, DEFAULT_SDK_VERSION, AndroidToolchain
from .collect_gradle_configs import MergedGradleConfig, collect_and_merge
from .gradle_project_builder import GradleProjectBuilder

Arch = KivySchoolData.AndroidData.Arch

_ARCH_TO_PLATFORM_CLS: dict[Arch, type[AndroidPlatform]] = {
    Arch.ARM64_V8A: AndroidArm64Platform,
    Arch.X86_64: AndroidX86_64Platform,
}


class GradleProjectError(Exception):
    pass


class GradleProject:

    adb: ADB
    emulator: AndroidEmulator
    _toolchain: AndroidToolchain | None
    builder: GradleProjectBuilder

    def __init__(self, project_path: Path):
        project_path = Path(project_path).resolve()
        if not (project_path / "pyproject.toml").is_file():
            raise GradleProjectError(f"No pyproject.toml found at {project_path}")

        self.project_path = project_path
        self.pyproject = PyProjectToml(str(project_path / "pyproject.toml"))

        kivy_school = self.pyproject.tool.kivy_school
        if kivy_school is None:
            raise GradleProjectError(
                "[tool.kivy-school] section is missing in pyproject.toml"
            )
        if kivy_school.android is None:
            raise GradleProjectError(
                "[tool.kivy-school.android] section is missing in pyproject.toml"
            )

        self.builder = GradleProjectBuilder(self.pyproject, project_path)
        self._toolchain = None

        # Determine SDK version from pyproject.toml for the emulator.
        # Prefer android.api, fall back to android.sdk, then the toolchain default.
        android_data = self.builder.android
        sdk_version = (
            (android_data.sdk or str(android_data.api) if android_data.api else DEFAULT_SDK_VERSION)
            if android_data
            else DEFAULT_SDK_VERSION
        )

        # Try lightweight SDK lookup (no downloads). Falls back to full resolve
        # only when needed (via the toolchain property).
        sdk_path = AndroidToolchain.find_sdk_path(self.builder.android, project_path)
        if sdk_path is not None:
            self.adb = ADB(sdk_path)
            self.emulator = AndroidEmulator(sdk_path, sdk_version)
        else:
            # SDK not yet installed — adb/emulator will be set up after
            # toolchain resolution (triggered by build).
            self.adb = None  # type: ignore[assignment]
            self.emulator = None  # type: ignore[assignment]

    @property
    def toolchain(self) -> AndroidToolchain:
        """Full toolchain resolution (may download SDK/NDK/Java). Only needed for builds."""
        if self._toolchain is None:
            self._toolchain = AndroidToolchain.resolve(
                self.builder.android, self.project_path
            )
            # Now that toolchain is resolved, ensure adb/emulator are set up.
            if self.adb is None:
                android_data = self.builder.android
                sdk_version = (
                    (android_data.sdk or str(android_data.api) if android_data.api else DEFAULT_SDK_VERSION)
                    if android_data
                    else DEFAULT_SDK_VERSION
                )
                self.adb = ADB(self._toolchain.sdk_path)
                self.emulator = AndroidEmulator(
                    self._toolchain.sdk_path, sdk_version
                )
        return self._toolchain

    # ------------------------------------------------------------------
    # Build pipeline
    # ------------------------------------------------------------------

    @property
    def gradle_dir(self) -> Path:
        return self.project_path / "project_dist" / "gradle"

    def generate(
        self,
        aar: bool = False,
        extra_gradle_dependencies: list[str] | None = None,
        extra_permissions: list[str] | None = None,
    ) -> None:
        """Write Gradle files, build CPython, copy stdlib + jniLibs."""
        self.builder.generate(
            aar=aar,
            extra_gradle_dependencies=extra_gradle_dependencies or [],
            extra_permissions=extra_permissions or [],
        )

    def install_site_packages(self) -> None:
        """Install the project (and its deps) into per-arch site_packages dirs."""
        for arch in self.builder.archs:
            cls = _ARCH_TO_PLATFORM_CLS.get(arch)
            if cls is None:
                raise GradleProjectError(f"No AndroidPlatform mapping for arch {arch}")
            platform = cls(str(self.project_path))
            Path(platform.site_packages).mkdir(parents=True, exist_ok=True)
            PipInstaller.install(
                uv_src=str(self.project_path),
                platform=platform,
                site_packages=platform.site_packages,
            )

    def gradle_assemble(
        self, variant: str = "debug", aar: bool = False, bundle: bool = False
    ) -> Path:
        if variant not in ("debug", "release"):
            raise GradleProjectError(
                f"Unknown variant {variant!r}; expected 'debug' or 'release'"
            )

        if aar:
            task = "assembleDebug" if variant == "debug" else "assembleRelease"
        elif bundle:
            task = "bundleDebug" if variant == "debug" else "bundleRelease"
        else:
            task = "assembleDebug" if variant == "debug" else "assembleRelease"

        env = os.environ.copy()
        env["JAVA_HOME"] = self.toolchain.java_path
        if sys.platform == "linux" and "JAVA_TOOL_OPTIONS" not in env:
            env["JAVA_TOOL_OPTIONS"] = "-XX:TieredStopAtLevel=1 -Xshare:off"

        gradlew = self.gradle_dir / (
            "gradlew.bat" if sys.platform == "win32" else "gradlew"
        )
        use_shell = sys.platform == "win32"

        if not gradlew.exists():
            raise GradleProjectError(
                f"Gradle project not generated yet: {gradlew} missing."
            )

        result = subprocess.run(
            [str(gradlew), task], cwd=self.gradle_dir, env=env, shell=use_shell
        )
        if result.returncode != 0:
            raise GradleProjectError(
                f"./gradlew {task} exited with code {result.returncode}"
            )

        if aar:
            output = (
                self.gradle_dir / "app" / "build" / "outputs" / "aar" / f"app-{variant}.aar"
            )
        elif bundle:
            output = (
                self.gradle_dir
                / "app"
                / "build"
                / "outputs"
                / "bundle"
                / variant
                / f"app-{variant}.aab"
            )
        else:
            output = (
                self.gradle_dir
                / "app"
                / "build"
                / "outputs"
                / "apk"
                / variant
                / f"app-{variant}.apk"
            )

        if not output.exists():
            raise GradleProjectError(f"Expected build artifact not found at {output}")

        return output

    def build(self, variant: str = "debug", aar: bool = False, bundle: bool = False) -> Path:
        """Run full pipeline: pip install → collect .gradle configs → generate → gradlew assemble/bundle."""
        self.install_site_packages()
        merged = self._collect_site_gradle_configs()
        self.generate(
            aar=aar,
            extra_gradle_dependencies=merged.gradle_dependencies,
            extra_permissions=merged.permissions,
        )
        return self.gradle_assemble(variant, aar=aar, bundle=bundle)

    def _collect_site_gradle_configs(self) -> MergedGradleConfig:
        """Scan all per-arch site_packages dirs for .gradle/*.json and merge."""
        sp_dirs = []
        for arch in self.builder.archs:
            cls = _ARCH_TO_PLATFORM_CLS.get(arch)
            if cls is None:
                continue
            platform = cls(str(self.project_path))
            sp_dir = Path(platform.site_packages)
            if sp_dir.is_dir():
                sp_dirs.append(sp_dir)
        return collect_and_merge(sp_dirs)

    # ------------------------------------------------------------------
    # Devices / run
    # ------------------------------------------------------------------

    def devices(self) -> list[dict]:
        """Combined list of attached adb devices and available AVDs."""
        if self.adb is None or self.emulator is None:
            raise GradleProjectError(
                "No Android SDK found. Run 'ksproject android build' first to "
                "install the toolchain, or set ANDROID_HOME / sdk_path in "
                "[tool.kivy-school.android]."
            )
        items: list[dict] = list(self.adb.devices())
        for name in self.emulator.list_avds():
            items.append({"name": name, "kind": "avd"})
        return items

    def find_apk(self, variant: str = "debug") -> Path:
        """Locate an existing APK for the given variant without rebuilding."""
        apk = (
            self.gradle_dir
            / "app"
            / "build"
            / "outputs"
            / "apk"
            / variant
            / f"app-{variant}.apk"
        )
        if not apk.exists():
            raise GradleProjectError(
                f"No APK found at {apk}. Run 'ksproject android build' first."
            )
        return apk

    def run(
        self,
        uuid: str | None = None,
        name: str | None = None,
        variant: str = "debug",
    ) -> None:
        if (uuid is None) == (name is None):
            raise GradleProjectError("run requires exactly one of uuid or name")

        if self.adb is None or self.emulator is None:
            raise GradleProjectError(
                "No Android SDK found. Run 'ksproject android build' first to "
                "install the toolchain, or set ANDROID_HOME / sdk_path in "
                "[tool.kivy-school.android]."
            )

        apk = self.find_apk(variant)

        if uuid is not None:
            serial = uuid
            self.adb.wait_for_device(serial)
        else:
            assert name is not None
            serial = self.emulator.boot_and_wait(name, self.adb)

        self.adb.install(apk, serial)
        self.adb.start_app(serial, self.builder.package_name)
