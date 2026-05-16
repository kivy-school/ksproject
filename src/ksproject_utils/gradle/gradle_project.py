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
from .android_toolchain import AndroidToolchain
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
    toolchain: AndroidToolchain
    builder: GradleProjectBuilder

    def __init__(self, project_path: Path):
        project_path = Path(project_path).resolve()
        if not (project_path / "pyproject.toml").is_file():
            raise GradleProjectError(
                f"No pyproject.toml found at {project_path}"
            )

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
        self.toolchain = AndroidToolchain.resolve(
            self.builder.android, project_path
        )
        self.adb = ADB(self.toolchain.sdk_path)
        sdk_version = str(
            (self.builder.android.api if self.builder.android else None) or 35
        )
        self.emulator = AndroidEmulator(self.toolchain.sdk_path, sdk_version)

    # ------------------------------------------------------------------
    # Build pipeline
    # ------------------------------------------------------------------

    @property
    def gradle_dir(self) -> Path:
        return self.project_path / "project_dist" / "gradle"

    def generate(self, aar: bool = False) -> None:
        """Write Gradle files, build CPython, copy stdlib + jniLibs."""
        self.builder.generate(aar=aar)

    def install_site_packages(self) -> None:
        """Install the project (and its deps) into per-arch site_packages dirs."""
        for arch in self.builder.archs:
            cls = _ARCH_TO_PLATFORM_CLS.get(arch)
            if cls is None:
                raise GradleProjectError(
                    f"No AndroidPlatform mapping for arch {arch}"
                )
            platform = cls(str(self.project_path))
            Path(platform.site_packages).mkdir(parents=True, exist_ok=True)
            PipInstaller.install(
                uv_src=str(self.project_path),
                platform=platform,
                site_packages=platform.site_packages,
            )

    def gradle_assemble(self, variant: str = "debug", aar: bool = False) -> Path:
        """Run only `gradlew assemble<Variant>` and return the produced APK or AAR."""
        if variant not in ("debug", "release"):
            raise GradleProjectError(
                f"Unknown variant {variant!r}; expected 'debug' or 'release'"
            )

        task = "assembleDebug" if variant == "debug" else "assembleRelease"
        env = os.environ.copy()
        env["JAVA_HOME"] = self.toolchain.java_path
        if sys.platform == "linux" and "JAVA_TOOL_OPTIONS" not in env:
            env["JAVA_TOOL_OPTIONS"] = "-XX:TieredStopAtLevel=1 -Xshare:off"
        if sys.platform == "win32":
            gradlew = self.gradle_dir / "gradlew.bat"
            use_shell = True
        else:
            gradlew = self.gradle_dir / "gradlew"
            use_shell = False
        if not gradlew.exists():
            raise GradleProjectError(
                f"Gradle project not generated yet: {gradlew} missing. "
                "Run `ksproject android build` first."
            )
        result = subprocess.run(
            [str(gradlew), task],
            cwd=self.gradle_dir,
            env=env,
            shell=use_shell,
        )
        if result.returncode != 0:
            raise GradleProjectError(
                f"./gradlew {task} exited with code {result.returncode}"
            )

        if aar:
            output = (
                self.gradle_dir
                / "app" / "build" / "outputs" / "aar"
                / f"app-{variant}.aar"
            )
            if not output.exists():
                raise GradleProjectError(f"Expected AAR not found at {output}")
        else:
            output = (
                self.gradle_dir
                / "app" / "build" / "outputs" / "apk"
                / variant / f"app-{variant}.apk"
            )
            if not output.exists():
                raise GradleProjectError(f"Expected APK not found at {output}")
        return output

    def build(self, variant: str = "debug", aar: bool = False) -> Path:
        """Run full pipeline: generate → pip install → gradlew assemble<Variant>.

        Returns the path to the produced APK or AAR.
        """
        self.generate(aar=aar)
        self.install_site_packages()
        return self.gradle_assemble(variant, aar=aar)

    # ------------------------------------------------------------------
    # Devices / run
    # ------------------------------------------------------------------

    def devices(self) -> list[dict]:
        """Combined list of attached adb devices and available AVDs."""
        items: list[dict] = list(self.adb.devices())
        for name in self.emulator.list_avds():
            items.append({"name": name, "kind": "avd"})
        return items

    def run(
        self,
        uuid: str | None = None,
        name: str | None = None,
        variant: str = "debug",
    ) -> None:
        if (uuid is None) == (name is None):
            raise GradleProjectError(
                "run requires exactly one of uuid or name"
            )

        if uuid is not None:
            serial = uuid
            self.adb.wait_for_device(serial)
        else:
            assert name is not None
            serial = self.emulator.boot_and_wait(name, self.adb)

        apk = self.gradle_assemble(variant)
        self.adb.install(apk, serial)
        self.adb.start_app(serial, self.builder.package_name)
