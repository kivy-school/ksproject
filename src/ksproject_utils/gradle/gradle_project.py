"""High-level Gradle/Android project orchestrator.

Single entrypoint used by both CLI and GUI: instantiate with a project path,
then call `build()`, `devices()`, or `run()`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from os import environ

from ..pip_install import PipInstaller
from ksp_bootstraps.platforms import (
    Platform,
    AndroidArm64Platform,
    AndroidPlatform,
    AndroidX86_64Platform,
)
from ksp_bootstraps.gradle.android_manifest_template import ANDROID_MANIFEST
from ksp_bootstraps.gradle.build_gradle_template import BUILD_GRADLE
from ..pyproject_toml import KivySchoolData, PyProjectToml
from .adb import ADB
from .android_emulator import AndroidEmulator
from .android_toolchain import (
    DEFAULT_API_VERSION,
    DEFAULT_SDK_VERSION,
    AndroidToolchain,
)
from .collect_gradle_configs import MergedGradleConfig, collect_and_merge

from .cpython_android import (
    ANDROID_VERSION,
    PY_VERSION,
    android_prefix,
    install_cpython_android,
)

# from .gradle_project_builder import GradleProjectBuilder
from ksp_bootstraps.bootstrap import BootstrapProtocol
from ksp_bootstraps.bootstraps import get_bootstrap
from ..python_version import read_python_version_pin

Arch = KivySchoolData.AndroidData.Arch

_ARCH_TO_PLATFORM_CLS: dict[Arch, type[AndroidPlatform]] = {
    Arch.ARM64_V8A: AndroidArm64Platform,
    Arch.X86_64: AndroidX86_64Platform,
}


class GradleProjectError(Exception):
    pass


class GradleProjectDelegate:
    working_dir: Path
    data: KivySchoolData.AndroidData
    # bootstrap: BootstrapProtocol
    toolchain: AndroidToolchain

    def __init__(
        self,
        working_dir: Path,
        data: KivySchoolData.AndroidData,
        toolchain: AndroidToolchain,
    ) -> None:
        self.working_dir = working_dir
        self.data = data
        self.toolchain = toolchain
        self.py_pin = read_python_version_pin(working_dir)

    def install_cpython(self):
        data = self.data
        toolchain = self.toolchain
        install_cpython_android(
            data.kivyschool_root(self.working_dir),
            [arch.value for arch in data.archs],
            toolchain.sdk_path,
            toolchain.ndk_path,
            toolchain.java_path,
            py_version=self.py_version,
            android_version=self.android_py_version,
        )

    def android_prefix(self, ks_root: Path, arch: str, android_version: str) -> Path:
        return android_prefix(ks_root, arch, android_version)

    @property
    def default_api_version(self) -> int:
        return DEFAULT_API_VERSION

    @property
    def sdk_path(self) -> str: ...

    @property
    def ndk_version(self) -> str:
        return self.toolchain.ndk_version

    @property
    def ndk_path(self) -> str:
        return self.toolchain.ndk_path

    @property
    def java_path(self) -> str:
        return self.toolchain.java_path

    @property
    def android_py_version(self) -> str:
        return self.py_pin.resolve(ANDROID_VERSION)

    @property
    def py_version(self) -> str:
        return self.py_pin.major_minor_or(PY_VERSION)

    @property
    def uv_py_version(self) -> str:
        """Exact version for `uv run --python` pins in generated scripts."""
        return self.py_pin.full_or(self.py_version)


class GradleProject:

    adb: ADB
    emulator: AndroidEmulator
    _toolchain: AndroidToolchain | None
    bootstrap: BootstrapProtocol
    pyproject: PyProjectToml

    def __init__(self, project_path: Path = Path.cwd()) -> None:
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
        self.android_data = kivy_school.android

        self._toolchain = None

        # Determine SDK version from pyproject.toml for the emulator.
        # Prefer android.api, fall back to android.sdk, then the toolchain default.
        android_data = kivy_school.android
        self.android_data = android_data
        sdk_version = (
            (
                android_data.sdk or str(android_data.api)
                if android_data.api
                else DEFAULT_SDK_VERSION
            )
            if android_data
            else DEFAULT_SDK_VERSION
        )

        # Try lightweight SDK lookup (no downloads). Falls back to full resolve
        # only when needed (via the toolchain property).
        sdk_path = AndroidToolchain.find_sdk_path(android_data, project_path)
        if sdk_path is not None:
            self.adb = ADB(sdk_path)
            self.emulator = AndroidEmulator(sdk_path, sdk_version)
        else:
            # SDK not yet installed — adb/emulator will be set up after
            # toolchain resolution (triggered by build).
            self.adb = None  # type: ignore[assignment]
            self.emulator = None  # type: ignore[assignment]

        # self.builder = GradleProjectBuilder(self.pyproject, project_path)
        delegate = GradleProjectDelegate(
            project_path, kivy_school.android, self.toolchain
        )

        self.bootstrap = get_bootstrap(
            name=kivy_school.bootstrap, pyproject=self.pyproject, delegate=delegate
        )

    @property
    def toolchain(self) -> AndroidToolchain:
        """Full toolchain resolution (may download SDK/NDK/Java). Only needed for builds."""
        if self._toolchain is None:
            self._toolchain = AndroidToolchain.resolve(
                self.android_data, self.project_path
            )
            # Now that toolchain is resolved, ensure adb/emulator are set up.
            if self.adb is None:
                android_data = self.android_data
                sdk_version = (
                    (
                        android_data.sdk or str(android_data.api)
                        if android_data.api
                        else DEFAULT_SDK_VERSION
                    )
                    if android_data
                    else DEFAULT_SDK_VERSION
                )
                self.adb = ADB(self._toolchain.sdk_path)
                self.emulator = AndroidEmulator(self._toolchain.sdk_path, sdk_version)
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
        self.bootstrap.generate(
            platform="android",
            aar=aar,
            extra_gradle_dependencies=extra_gradle_dependencies or [],
            extra_permissions=extra_permissions or [],
            sdk_path=self.toolchain.sdk_path,
        )

    def platform_pre_build_script(self):

        script = self.android_data.pre_build

        env = {**environ}

        if script:
            cur = Path.cwd()
            env["WHEELHOUSE"] = f"{cur / "wheelhouse"}"
            match script.suffix:
                case ".py":
                    subprocess.run(
                        ["uv", "run", str(script.absolute())], check=True, env=env
                    )
                case _:
                    subprocess.run([str(script.absolute())], check=True, env=env)

    def install_site_packages(self) -> None:
        """Install the project (and its deps) into per-arch site_packages dirs."""
        for arch in self.android_data.archs:
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

    def generate_templates(self, force: bool = False) -> None:
        """Generate or regenerate Android project template files.

        Args:
            force: If True, overwrite existing template files.
        """
        self._ensure_android_manifest(force=force)
        self._ensure_build_gradle_template(force=force)

    def _ensure_android_manifest(self, force: bool = False) -> None:
        tmpl_path = self.project_path / "AndroidManifest.tmpl.xml"
        if force or not tmpl_path.exists():
            tmpl_path.write_text(
                self.default_android_manifest_template(), encoding="utf-8"
            )
            print(f"[ksproject] {'Overwrote' if force else 'Generated'} {tmpl_path.name}")
        else:
            print(f"[ksproject] {tmpl_path.name} already exists. Use --force to overwrite.")

    def default_android_manifest_template(self) -> str:
        return ANDROID_MANIFEST

    def _ensure_build_gradle_template(self, force: bool = False) -> None:
        tmpl_path = self.project_path / "build.tmpl.gradle.kts"
        if force or not tmpl_path.exists():
            tmpl_path.write_text(self.default_build_gradle_template(), encoding="utf-8")
            print(f"[ksproject] {'Overwrote' if force else 'Generated'} {tmpl_path.name}")
        else:
            print(f"[ksproject] {tmpl_path.name} already exists. Use --force to overwrite.")

    def default_build_gradle_template(self) -> str:
        return BUILD_GRADLE

    def gradle_assemble(
        self,
        variant: str = "debug",
        aar: bool = False,
        bundle: bool = False,
        clean: bool = False,
    ) -> list[Path]:
        if variant not in ("debug", "release"):
            raise GradleProjectError(
                f"Unknown variant {variant!r}; expected 'debug' or 'release'"
            )

        if aar:
            task = "assembleDebug" if variant == "debug" else "assembleRelease"
        elif bundle:
            task = "bundleDebug" if variant == "debug" else "bundleRelease"
        else:
            task = (
                "assembleDebug"
                if variant == "release"
                else "assembleDebug" if variant == "debug" else "assembleRelease"
            )

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

        args = [str(gradlew)]
        if clean:
            args.append("clean")
        args.append(task)

        cmd_str = " ".join(args[1:])
        print(f"[ksproject] Running Gradle task: {cmd_str}")
        result = subprocess.run(args, cwd=self.gradle_dir, env=env, shell=use_shell)
        if result.returncode != 0:
            raise GradleProjectError(
                f"./gradlew {cmd_str} exited with code {result.returncode}"
            )

        artifacts: list[Path] = []
        if aar:
            aar_dir = self.gradle_dir / "app" / "build" / "outputs" / "aar"
            artifacts = list(aar_dir.rglob(f"*{variant}*.aar"))
        elif bundle:
            artifacts = self.find_bundles(variant)
        else:
            artifacts = self.find_apks(variant)

        if not artifacts:
            raise GradleProjectError("Expected build artifacts were not produced.")

        if len(artifacts) > 1:
            print(f"\n[ksproject] Found {len(artifacts)} artifacts:")
            for art in artifacts:
                print(f"  • {art.name} ({art.parent.name}) -> {art}")
        else:
            print(f"APK: {artifacts[0]}")

        return artifacts

    def build(
        self,
        variant: str = "debug",
        aar: bool = False,
        bundle: bool = False,
        clean: bool = False,
    ) -> list[Path]:
        """Run full pipeline: pip install -> collect configs -> generate -> assemble/bundle."""
        self.platform_pre_build_script()
        self.install_site_packages()
        merged = self._collect_site_gradle_configs()
        self.generate(
            aar=aar,
            extra_gradle_dependencies=merged.gradle_dependencies,
            extra_permissions=merged.permissions,
        )
        return self.gradle_assemble(variant, aar=aar, bundle=bundle, clean=clean)

    def _collect_site_gradle_configs(self) -> MergedGradleConfig:
        """Scan all per-arch site_packages dirs for .gradle/*.json and merge."""
        sp_dirs = []
        for arch in self.android_data.archs:
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

    def find_apks(
        self, variant: str = "debug", unsigned_only: bool = False
    ) -> list[Path]:
        """Locate all existing APKs for the given variant across all flavor folders."""
        apk_base_dir = self.gradle_dir / "app" / "build" / "outputs" / "apk"
        if not apk_base_dir.exists():
            return []

        apks: list[Path] = []
        for path in apk_base_dir.rglob(f"*{variant}*.apk"):
            if unsigned_only:
                if "-signed" not in path.name:
                    apks.append(path)
            else:
                apks.append(path)

        def sort_key(p: Path) -> int:
            if "-signed" in p.name:
                return 0
            elif "-unsigned" in p.name:
                return 2
            return 1

        return sorted(apks, key=sort_key)

    def find_apk(self, variant: str = "debug") -> Path:
        """Locate a single existing APK for commands like `run`."""
        apks = self.find_apks(variant)
        if not apks:
            raise GradleProjectError(
                f"No {variant} APK found in {self.gradle_dir / 'app' / 'build' / 'outputs' / 'apk'}. "
                "Run 'ksproject android build' first."
            )
        return apks[0]

    def find_bundles(
        self, variant: str = "release", unsigned_only: bool = False
    ) -> list[Path]:
        """Locate all existing AABs for the given variant."""
        bundle_base_dir = self.gradle_dir / "app" / "build" / "outputs" / "bundle"
        if not bundle_base_dir.exists():
            return []

        bundles: list[Path] = []
        for path in bundle_base_dir.rglob(f"*{variant}*.aab"):
            if unsigned_only:
                if "-signed" not in path.name:
                    bundles.append(path)
            else:
                bundles.append(path)

        return sorted(bundles)

    def find_bundle(self, variant: str = "release") -> Path:
        """Locate a single existing App Bundle."""
        bundles = self.find_bundles(variant)
        if not bundles:
            raise GradleProjectError(f"No {variant} App Bundle found.")
        return bundles[0]

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

        if uuid is not None:
            serial = uuid
            self.adb.wait_for_device(serial)
        else:
            assert name is not None
            serial = self.emulator.boot_and_wait(name, self.adb)

        device_abis = self.adb.get_device_abis(serial)
        print(f"[ksproject] Detected device ABIs: {', '.join(device_abis)}")

        apks = self.find_apks(variant)
        if not apks:
            raise GradleProjectError(
                f"No {variant} APKs found. Build the project first."
            )

        best_apk = None

        for abi in device_abis:
            gradle_flavor_name = abi.replace("-", "_")

            for apk in apks:
                if gradle_flavor_name in apk.name and "unsigned" not in apk.name:
                    best_apk = apk
                    break
                elif gradle_flavor_name in apk.name:
                    best_apk = apk

            if best_apk:
                print(f"[ksproject] Matched ABI '{abi}' -> Selected {best_apk.name}")
                break

        if not best_apk:
            best_apk = apks[0]
            print(
                f"[ksproject] No exact ABI match found. Falling back to: {best_apk.name}"
            )

        print(f"[ksproject] Installing {best_apk.name} on {serial}...")
        self.adb.install(best_apk, serial)
        self.adb.start_app(serial, self.android_data.package_name)

    # ------------------------------------------------------------------
    # Signing & Keystore Generation
    # ------------------------------------------------------------------

    def genkey(
        self,
        keystore_path: Path | str,
        storepass: str,
        keyalias: str,
        keypass: str | None = None,
        dname: str | None = None,
        validity: int = 10000,
    ) -> Path:
        """Generate a new secure Java Keystore (JKS) using keytool."""
        keystore_path = Path(keystore_path).resolve()
        if keystore_path.exists():
            raise GradleProjectError(
                f"Keystore file already exists at: {keystore_path}"
            )

        keystore_path.parent.mkdir(parents=True, exist_ok=True)

        java_home = Path(self.toolchain.java_path)
        keytool = (
            java_home
            / "bin"
            / ("keytool.exe" if sys.platform == "win32" else "keytool")
        )

        if not keytool.exists():
            raise GradleProjectError(
                f"keytool executable missing from JDK home at {keytool}"
            )

        if not dname:
            dname = "CN=KivySchoolApp, O=KivySchool, C=US"

        args = [
            str(keytool),
            "-genkeypair",
            "-v",
            "-keystore",
            str(keystore_path),
            "-alias",
            keyalias,
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            str(validity),
            "-storepass",
            storepass,
            "-dname",
            dname,
        ]

        if keypass:
            args.extend(["-keypass", keypass])
        else:
            args.extend(["-keypass", storepass])

        env = os.environ.copy()
        env["JAVA_HOME"] = self.toolchain.java_path
        use_shell = sys.platform == "win32"

        result = subprocess.run(
            args, env=env, shell=use_shell, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise GradleProjectError(
                f"keytool generation failed:\n{result.stderr or result.stdout}"
            )

        return keystore_path

    def sign_project_artifact(
        self,
        keystore: Path | str,
        storepass: str,
        keyalias: str,
        keypass: str | None = None,
        variant: str = "release",
        bundle: bool = False,
    ) -> list[Path]:
        """Finds all compiled artifacts for the variant and signs each one."""
        keystore_path = Path(keystore).resolve()
        signed_artifacts: list[Path] = []

        if bundle:
            raw_targets = self.find_bundles(variant, unsigned_only=True)
            if not raw_targets:
                raise GradleProjectError(f"No unsigned {variant} AABs found to sign.")
            print(f"[ksproject] Signing {len(raw_targets)} App Bundle(s)...")
            for target in raw_targets:
                signed = self._sign_aab(
                    target, keystore_path, storepass, keyalias, keypass
                )
                signed_artifacts.append(signed)
                print(f"  [✓] Signed AAB: {signed.name}")
        else:
            raw_targets = self.find_apks(variant, unsigned_only=True)
            if not raw_targets:
                raise GradleProjectError(f"No unsigned {variant} APKs found to sign.")
            print(f"[ksproject] Signing {len(raw_targets)} APK(s)...")
            for target in raw_targets:
                signed = self._sign_apk(
                    target, keystore_path, storepass, keyalias, keypass
                )
                signed_artifacts.append(signed)
                print(f"  [✓] Signed APK: {signed.name}")

        return signed_artifacts

    def _sign_apk(
        self,
        apk_path: Path,
        keystore: Path,
        storepass: str,
        keyalias: str,
        keypass: str | None = None,
    ) -> Path:
        sdk_path = Path(self.toolchain.sdk_path)
        build_tools_dir = sdk_path / "build-tools"

        if not build_tools_dir.is_dir():
            raise GradleProjectError(
                f"build-tools directory missing: {build_tools_dir}"
            )

        versions = sorted([d for d in build_tools_dir.iterdir() if d.is_dir()])
        if not versions:
            raise GradleProjectError(
                "No build-tools versions found to locate apksigner."
            )

        apksigner = versions[-1] / (
            "apksigner.bat" if sys.platform == "win32" else "apksigner"
        )
        if not apksigner.exists():
            raise GradleProjectError(f"apksigner executable missing at {apksigner}")

        signed_apk = apk_path.with_name(
            apk_path.name.replace("-unsigned", "-signed")
            if "-unsigned" in apk_path.name
            else f"{apk_path.stem}-signed.apk"
        )

        args = [
            str(apksigner),
            "sign",
            "--ks",
            str(keystore),
            "--ks-pass",
            f"pass:{storepass}",
            "--ks-key-alias",
            keyalias,
            "--out",
            str(signed_apk),
        ]
        if keypass:
            args.extend(["--key-pass", f"pass:{keypass}"])
        args.append(str(apk_path))

        self._run_signing_cmd(args)
        return signed_apk

    def _sign_aab(
        self,
        aab_path: Path,
        keystore: Path,
        storepass: str,
        keyalias: str,
        keypass: str | None = None,
    ) -> Path:
        java_home = Path(self.toolchain.java_path)
        jarsigner = (
            java_home
            / "bin"
            / ("jarsigner.exe" if sys.platform == "win32" else "jarsigner")
        )

        if not jarsigner.exists():
            raise GradleProjectError(
                f"jarsigner executable missing from JDK home at {jarsigner}"
            )

        signed_aab = aab_path.with_name(
            aab_path.name.replace("-unsigned", "-signed")
            if "-unsigned" in aab_path.name
            else f"{aab_path.stem}-signed.aab"
        )

        import shutil

        shutil.copy2(aab_path, signed_aab)

        args = [
            str(jarsigner),
            "-keystore",
            str(keystore),
            "-storepass",
            storepass,
            str(signed_aab),
            keyalias,
        ]
        if keypass:
            args.extend(["-keypass", keypass])

        self._run_signing_cmd(args)
        return signed_aab

    def _run_signing_cmd(self, args: list[str]) -> None:
        env = os.environ.copy()
        env["JAVA_HOME"] = self.toolchain.java_path
        use_shell = sys.platform == "win32"

        result = subprocess.run(
            args, env=env, shell=use_shell, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise GradleProjectError(
                f"Signing command failed:\n{result.stderr or result.stdout}"
            )
