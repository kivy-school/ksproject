"""Resolves the Android SDK, NDK, and Java paths needed to build the project.

Priority order for each tool:
  1. Explicit path set in [tool.kivy-school.android] (sdk_path / ndk_path / java_path)
  2. ksproject-managed install under <project_dir>/.kivyschool/android-sdk
  3. System environment variables (ANDROID_HOME, ANDROID_NDK_ROOT, JAVA_HOME)
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ..pyproject_toml import KivySchoolData


_CMDLINE_TOOLS_URLS = {
    "darwin": "https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip",
    "linux": "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip",
}
SDKMAN_INSTALL_URL = "https://get.sdkman.io"
DEFAULT_SDK_VERSION = "35"
DEFAULT_NDK_VERSION = "27.3.13750724"
DEFAULT_CMAKE_VERSION = "3.22.1"


def host_emulator_abi() -> str:
    """Pick a system-image ABI that matches the host CPU."""
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64-v8a"
    return "x86_64"


class AndroidToolchainError(Exception):
    pass


@dataclass
class AndroidToolchain:
    sdk_path: str
    ndk_path: str
    java_path: str
    ndk_version: str = ""

    @staticmethod
    def kivyschool_sdk_root(project_dir: Path) -> Path:
        return project_dir / ".kivyschool" / "android-sdk"

    @classmethod
    def resolve(
        cls,
        android: KivySchoolData.AndroidData | None,
        project_dir: Path,
    ) -> "AndroidToolchain":
        if sys.platform not in _CMDLINE_TOOLS_URLS:
            raise AndroidToolchainError(
                f"AndroidToolchain does not support platform: {sys.platform}"
            )

        sdk_version = (android.sdk if android else None) or DEFAULT_SDK_VERSION
        ndk_version = (android.ndk if android else None) or DEFAULT_NDK_VERSION

        # Java first — sdkmanager needs it
        java_path = _resolve_java(android)
        sdk_path = _resolve_sdk(
            android, sdk_version, ndk_version, java_path, project_dir
        )
        ndk_path = _resolve_ndk(android, sdk_path, ndk_version)
        _ensure_emulator(sdk_path, sdk_version, java_path)

        return cls(
            sdk_path=sdk_path,
            ndk_path=ndk_path,
            java_path=java_path,
            ndk_version=ndk_version,
        )


# ---------------------------------------------------------------------------
# SDK
# ---------------------------------------------------------------------------

def _resolve_sdk(
    android: KivySchoolData.AndroidData | None,
    sdk_version: str,
    ndk_version: str,
    java_path: str,
    project_dir: Path,
) -> str:
    if android and android.sdk_path:
        return str(android.sdk_path)

    managed = AndroidToolchain.kivyschool_sdk_root(project_dir)
    platforms_dir = managed / "platforms" / f"android-{sdk_version}"
    if not platforms_dir.exists():
        _install_sdk(managed, sdk_version, ndk_version, java_path)
    # CMake is required by AGP's externalNativeBuild but wasn't always
    # installed in older runs. Top it up if missing.
    if not (managed / "cmake" / DEFAULT_CMAKE_VERSION / "bin" / "cmake").exists():
        _sdkmanager_install(
            managed, java_path, [f"cmake;{DEFAULT_CMAKE_VERSION}"]
        )
    return str(managed)


def _resolve_ndk(
    android: KivySchoolData.AndroidData | None,
    sdk_path: str,
    ndk_version: str,
) -> str:
    if android and android.ndk_path:
        return str(android.ndk_path)

    ndk_in_sdk = Path(sdk_path) / "ndk" / ndk_version
    if ndk_in_sdk.exists():
        return str(ndk_in_sdk)

    env = os.environ.get("ANDROID_NDK_ROOT")
    if env:
        return env

    raise AndroidToolchainError(
        f"Android NDK {ndk_version} not found. Set ndk_path in "
        f"[tool.kivy-school.android] or ensure sdkmanager installed it."
    )


def _install_sdk(
    sdk_root: Path, sdk_version: str, ndk_version: str, java_path: str
) -> None:
    sdk_root.mkdir(parents=True, exist_ok=True)

    cmdline_tools_zip = sdk_root / "commandlinetools.zip"
    cmdline_tools_dir = sdk_root / "cmdline-tools"
    sdkmanager = cmdline_tools_dir / "latest" / "bin" / "sdkmanager"

    if not sdkmanager.exists():
        print("[ksproject] Downloading Android cmdline-tools...")
        url = _CMDLINE_TOOLS_URLS[sys.platform]
        urllib.request.urlretrieve(url, cmdline_tools_zip)

        cmdline_tools_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(cmdline_tools_zip) as zf:
            zf.extractall(cmdline_tools_dir)

        # sdkmanager requires the directory to be named "latest"
        unpacked = cmdline_tools_dir / "cmdline-tools"
        if unpacked.exists():
            unpacked.rename(cmdline_tools_dir / "latest")
        cmdline_tools_zip.unlink(missing_ok=True)

        # Restore exec bit lost on some unzip paths
        os.chmod(sdkmanager, 0o755)

    env = os.environ.copy()
    env["ANDROID_HOME"] = str(sdk_root)
    env["JAVA_HOME"] = java_path

    packages = [
        "platform-tools",
        "emulator",
        f"platforms;android-{sdk_version}",
        f"build-tools;{sdk_version}.0.0",
        f"ndk;{ndk_version}",
        f"cmake;{DEFAULT_CMAKE_VERSION}",
        f"system-images;android-{sdk_version};google_apis;{host_emulator_abi()}",
    ]

    print(
        f"[ksproject] Installing Android SDK platform {sdk_version} "
        f"and NDK {ndk_version}..."
    )

    # Accept licenses first
    _run_sdkmanager(
        str(sdkmanager), ["--licenses"], env=env, stdin_input="y\n" * 5
    )

    for pkg in packages:
        _run_sdkmanager(str(sdkmanager), ["--install", pkg], env=env)

    print(f"[ksproject] Android toolchain installed at {sdk_root}")


def _sdkmanager_install(
    sdk_root: Path, java_path: str, packages: list[str]
) -> None:
    sdkmanager = sdk_root / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
    if not sdkmanager.exists():
        raise AndroidToolchainError(
            f"sdkmanager not found at {sdkmanager}; reinstall the SDK"
        )
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(sdk_root)
    env["JAVA_HOME"] = java_path
    print(f"[ksproject] Installing missing SDK packages: {', '.join(packages)}")
    for pkg in packages:
        _run_sdkmanager(str(sdkmanager), ["--install", pkg], env=env)


def _run_sdkmanager(
    sdkmanager: str,
    args: list[str],
    env: dict[str, str],
    stdin_input: str | None = None,
) -> None:
    result = subprocess.run(
        [sdkmanager, *args],
        env=env,
        input=stdin_input,
        text=True,
    )
    if result.returncode != 0:
        raise AndroidToolchainError(
            f"sdkmanager '{' '.join(args)}' exited with code {result.returncode}"
        )


def _ensure_emulator(sdk_path: str, sdk_version: str, java_path: str) -> None:
    """Install the emulator + a host-arch system image if missing.

    Allows users who installed the SDK earlier (without emulator support) to
    pick up the new packages on next invocation.
    """
    sdk_root = Path(sdk_path)
    emulator_bin = sdk_root / "emulator" / "emulator"
    abi = host_emulator_abi()
    sysimg_dir = (
        sdk_root / "system-images" / f"android-{sdk_version}" / "google_apis" / abi
    )
    if emulator_bin.exists() and sysimg_dir.exists():
        return

    sdkmanager = sdk_root / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
    if not sdkmanager.exists():
        # No SDK manager — skip silently; callers needing the emulator will
        # surface a clearer error.
        return

    env = os.environ.copy()
    env["ANDROID_HOME"] = str(sdk_root)
    env["JAVA_HOME"] = java_path

    print(f"[ksproject] Installing Android emulator + system image ({abi})...")
    if not emulator_bin.exists():
        _run_sdkmanager(str(sdkmanager), ["--install", "emulator"], env=env)
    if not sysimg_dir.exists():
        _run_sdkmanager(
            str(sdkmanager),
            [
                "--install",
                f"system-images;android-{sdk_version};google_apis;{abi}",
            ],
            env=env,
            stdin_input="y\n",
        )


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------

def _resolve_java(android: KivySchoolData.AndroidData | None) -> str:
    if android and android.java_path:
        return str(android.java_path)

    sdkman_current = Path.home() / ".sdkman" / "candidates" / "java" / "current"
    if sdkman_current.exists():
        return str(sdkman_current)

    env = os.environ.get("JAVA_HOME")
    if env:
        return env

    detected = _detect_system_java_home()
    if detected:
        return detected

    return _install_java_via_sdkman()


def _detect_system_java_home() -> str | None:
    # macOS: /usr/libexec/java_home
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["/usr/libexec/java_home"], capture_output=True, text=True
            )
        except FileNotFoundError:
            return None
        if result.returncode != 0:
            return None
        out = result.stdout.strip()
        return out or None

    # Linux: resolve JAVA_HOME from the javac symlink chain
    try:
        result = subprocess.run(
            ["which", "javac"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return None
        javac = Path(result.stdout.strip()).resolve()
        # <java_home>/bin/javac → go up two levels
        java_home = javac.parent.parent
        return str(java_home) if java_home.exists() else None
    except Exception:
        return None


def _install_java_via_sdkman() -> str:
    sdkman_init = Path.home() / ".sdkman" / "bin" / "sdkman-init.sh"

    if not sdkman_init.exists():
        print("[ksproject] Installing sdkman...")
        installer = subprocess.run(
            ["curl", "-s", SDKMAN_INSTALL_URL],
            capture_output=True,
            text=True,
            check=True,
        )
        proc = subprocess.run(
            ["/bin/bash"], input=installer.stdout, text=True
        )
        if proc.returncode != 0:
            raise AndroidToolchainError(
                f"sdkman installer exited with code {proc.returncode}"
            )

    print("[ksproject] Installing Java (Temurin LTS) via sdkman...")
    proc = subprocess.run(
        [
            "/bin/bash",
            "-c",
            f'source "{sdkman_init}" && sdk install java',
        ],
    )
    if proc.returncode != 0:
        raise AndroidToolchainError(
            f"'sdk install java' exited with code {proc.returncode}"
        )

    installed = Path.home() / ".sdkman" / "candidates" / "java" / "current"
    if not installed.exists():
        raise AndroidToolchainError(
            "Java installation via sdkman failed. Set java_path in "
            "[tool.kivy-school.android] to point to an existing JDK."
        )
    print(f"[ksproject] Java installed at {installed}")
    return str(installed)
