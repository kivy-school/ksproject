"""Android build test — runs the real ``ksproject android build`` CLI command.

This downloads the Android SDK/NDK toolchain on first run (ksproject manages
that itself) and produces a real APK from the ``minimal_app`` fixture.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.android


def test_android_build(minimal_app: Path) -> None:
    """``ksproject android build`` exits 0 and prints an APK path that exists."""
    result = subprocess.run(
        ["ksproject", "android", "build"],
        cwd=minimal_app,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"ksproject android build failed:\n{result.stdout}\n{result.stderr}"
    )
    apk_line = next(
        (line for line in result.stdout.splitlines() if line.startswith("APK:")),
        None,
    )
    assert apk_line is not None, f"No APK: line in stdout:\n{result.stdout}"
    apk = Path(apk_line.split("APK:", 1)[1].strip())
    assert apk.exists(), f"APK reported but not on disk: {apk}"
