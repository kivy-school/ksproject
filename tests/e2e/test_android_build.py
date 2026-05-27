"""Android build test — runs the real ``ksproject android build`` CLI command.

This downloads the Android SDK/NDK toolchain on first run (ksproject manages
that itself) and produces a real APK from the ``minimal_app`` fixture.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import pytest

from ksproject_utils.gradle.android_emulator import (
    AndroidEmulatorError,
    DEFAULT_AVD_DEVICE,
    DEFAULT_AVD_NAME,
)
from ksproject_utils.gradle.android_toolchain import host_emulator_abi
from ksproject_utils.gradle.gradle_project import GradleProject

pytestmark = pytest.mark.android


def _ksproject() -> str:
    """Path to the ksproject script in the current venv."""
    _bin = Path(sys.executable).parent
    return str(_bin / ("ksproject.exe" if sys.platform == "win32" else "ksproject"))


def _stream(proc: subprocess.Popen) -> tuple[list[str], int]:
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        lines.append(line)
    return lines, proc.wait()


def _adb() -> str:
    """Locate adb in ANDROID_HOME or on PATH."""
    import os
    from pathlib import Path as P
    home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT", "")
    if home:
        candidate = P(home) / "platform-tools" / "adb"
        if candidate.exists():
            return str(candidate)
    return "adb"


def test_android_build_produces_apk(minimal_app: Path) -> None:
    """``ksproject android build`` exits 0 and prints an APK path that exists."""
    proc = subprocess.Popen(
        [_ksproject(), "android", "build"],
        cwd=minimal_app,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines, returncode = _stream(proc)
    output = "".join(lines)
    assert returncode == 0, f"ksproject android build failed:\n{output}"
    apk_line = next((l for l in lines if l.startswith("APK:")), None)
    assert apk_line is not None, f"No APK: line in stdout:\n{output}"
    apk = Path(apk_line.split("APK:", 1)[1].strip())
    assert apk.exists(), f"APK reported but not on disk: {apk}"


def test_android_emulator_unittests_pass(minimal_app: Path) -> None:
    """Build APK, install on a running emulator/device, push an adb marker
    file so the app runs its in-app unittest suite, stream logcat, and
    assert KSPROJECT_TEST_RESULT: PASS."""
    if sys.platform != "linux":
        pytest.skip("Android emulator test requires Linux with KVM")
    # --- Build ---
    proc = subprocess.Popen(
        [_ksproject(), "android", "build"],
        cwd=minimal_app,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    build_lines, rc = _stream(proc)
    build_output = "".join(build_lines)
    assert rc == 0, f"android build failed:\n{build_output}"
    apk_line = next((l for l in build_lines if l.startswith("APK:")), None)
    assert apk_line is not None
    apk = Path(apk_line.split("APK:", 1)[1].strip())

    # --- Derive package name the same way GradleProjectBuilder does ---
    data = tomllib.loads((minimal_app / "pyproject.toml").read_text())
    project_name = data["project"]["name"]
    pkg = f"org.kivyschool.{project_name}"

    # Always use ksproject's own adb (installed during android build).
    project = GradleProject(minimal_app)
    adb = project.adb.binary  # str path for subprocess; project.adb (ADB object) for boot_and_wait

    # --- Find a running device/emulator, or create+boot the default AVD ---
    r = subprocess.run([adb, "devices", "-l"], capture_output=True, text=True)
    attached = [
        line.split()[0]
        for line in r.stdout.splitlines()[1:]
        if line.strip() and "device" in line.split()[1:]
    ]
    if attached:
        serial = attached[0]
        print(f"Device: {serial}")
    else:
        if project.emulator is None:
            pytest.skip("No Android device/emulator and no emulator binary found")
        # ensure_default_avd() silently returns rc=0 but doesn't create the AVD
        # when avdmanager can't find the system image (no ANDROID_SDK_ROOT set).
        # Create the AVD ourselves with explicit env vars and verify the ini file.
        avd_home = Path.home() / ".android" / "avd"
        avd_home.mkdir(parents=True, exist_ok=True)
        avd_ini = avd_home / f"{DEFAULT_AVD_NAME}.ini"
        if not avd_ini.exists():
            abi = host_emulator_abi()
            system_image = (
                f"system-images;android-{project.emulator.sdk_version}"
                f";google_apis;{abi}"
            )
            avd_env = {
                **os.environ,
                "ANDROID_SDK_ROOT": project.emulator.sdk_path,
                "ANDROID_AVD_HOME": str(avd_home),
            }
            create = subprocess.run(
                [
                    project.emulator.avdmanager, "create", "avd",
                    "-n", DEFAULT_AVD_NAME, "-k", system_image,
                    "-d", DEFAULT_AVD_DEVICE, "-f",
                ],
                input="no\n",
                env=avd_env,
                capture_output=True,
                text=True,
            )
            avd_output = (create.stdout or "") + (create.stderr or "")
            if create.returncode != 0 or not avd_ini.exists():
                pytest.fail(
                    f"avdmanager create avd failed (rc={create.returncode}):\n{avd_output}"
                )
            print(f"Created AVD: {DEFAULT_AVD_NAME}\n{avd_output.strip()}")
        print(f"Booting AVD: {DEFAULT_AVD_NAME}")
        try:
            serial = project.emulator.boot_and_wait(DEFAULT_AVD_NAME, project.adb)
        except (AndroidEmulatorError, OSError) as exc:
            pytest.fail(f"AVD {DEFAULT_AVD_NAME} failed to boot: {exc}")

    # --- Install ---
    subprocess.run([adb, "-s", serial, "install", "-r", str(apk)], check=True)

    # --- Push test marker file (tells __main__.py to run tests) ---
    subprocess.run(
        [adb, "-s", serial, "shell", "echo 1 > /data/local/tmp/.ksproject_test"],
        check=True,
    )

    # --- Clear logcat, launch ---
    subprocess.run([adb, "-s", serial, "logcat", "-c"], check=True)
    subprocess.run(
        [adb, "-s", serial, "shell", "am", "start", "-S",
         "-n", f"{pkg}/.MainActivity"],
        check=True,
    )

    # --- Stream logcat (python tag only) for sentinels ---
    logcat = subprocess.Popen(
        [adb, "-s", serial, "logcat", "-s", "python:V"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    sentinel_result: int | None = None
    totals_seen = False
    deadline = time.monotonic() + 300
    try:
        assert logcat.stdout is not None
        for line in logcat.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            if "KSPROJECT_TEST_RESULT:" in line:
                sentinel_result = 0 if "PASS" in line else 1
            if "KSPROJECT_TEST_TOTALS:" in line:
                totals_seen = True
            if sentinel_result is not None and totals_seen:
                break
            if time.monotonic() > deadline:
                pytest.fail("Timed out waiting for KSPROJECT_TEST_RESULT sentinel")
    finally:
        logcat.terminate()
        subprocess.run(
            [adb, "-s", serial, "shell", "am", "force-stop", pkg],
            check=False,
        )

    assert sentinel_result == 0, "In-app tests did not PASS"

