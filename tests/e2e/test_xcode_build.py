"""Apple build tests — run the real ``ksproject ios build --sim`` CLI command.

macOS only. Downloads xcframeworks on first run (ksproject manages that).
"""
from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.apple


def _ksproject() -> str:
    """Path to the ksproject script in the current venv."""
    _bin = Path(sys.executable).parent
    return str(_bin / "ksproject")


@pytest.fixture(autouse=True)
def _macos_only() -> None:
    if platform.system() != "Darwin":
        pytest.skip("Apple tests require macOS")


def test_ios_simulator_build_produces_app(minimal_app: Path) -> None:
    """``ksproject ios build --sim`` exits 0 and produces a .app."""
    result = subprocess.run(
        [_ksproject(), "ios", "build", "--sim"],
        cwd=minimal_app,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"ksproject ios build --sim failed:\n{result.stdout}\n{result.stderr}"
    )
    app_line = next(
        (line for line in result.stdout.splitlines() if line.startswith("app:")),
        None,
    )
    assert app_line is not None, f"No app: line in stdout:\n{result.stdout}"
    app = Path(app_line.split("app:", 1)[1].strip())
    assert app.exists(), f".app reported but not on disk: {app}"
