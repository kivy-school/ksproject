"""Apple build tests — run the real ``ksproject ios build --sim`` CLI command.

macOS only. Downloads xcframeworks on first run (ksproject manages that).
"""
from __future__ import annotations

import json
import os
import platform
import plistlib
import subprocess
import sys
import time
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


def _stream(proc: subprocess.Popen) -> tuple[list[str], int]:
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        lines.append(line)
    return lines, proc.wait()


def test_ios_simulator_build_produces_app(minimal_app: Path) -> None:
    """``ksproject ios build --sim`` exits 0 and produces a .app."""
    proc = subprocess.Popen(
        [_ksproject(), "ios", "build", "--sim"],
        cwd=minimal_app,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines, returncode = _stream(proc)
    output = "".join(lines)
    assert returncode == 0, f"ksproject ios build --sim failed:\n{output}"
    app_line = next((l for l in lines if l.startswith("app:")), None)
    assert app_line is not None, f"No app: line in stdout:\n{output}"
    app = Path(app_line.split("app:", 1)[1].strip())
    assert app.exists(), f".app reported but not on disk: {app}"


def test_ios_simulator_unittests_pass(minimal_app: Path) -> None:
    """Build the .app, boot a simulator, launch with KSPROJECT_TEST=1 via
    SIMCTL_CHILD_ prefix, and assert the in-app suite prints a PASS sentinel."""
    project = XcodeProject(minimal_app)
    app = project.ios_build(simulator=True)
    bundle_id = project._bundle_id()

    # --- Pick first available iOS simulator ---
    sims = [
        s for s in project._list_simulators()
        if "iOS" in s.get("runtime", "")
        or "iphonesimulator" in s.get("runtime", "").lower()
    ]
    assert sims, "No iOS simulator available"
    sim_uuid = sims[0]["uuid"]
    print(f"Simulator: {sims[0]['name']} ({sim_uuid})")

    # --- Boot + install ---
    subprocess.run(
        ["xcrun", "simctl", "boot", sim_uuid],
        check=False, capture_output=True,
    )
    subprocess.run(
        ["xcrun", "simctl", "install", sim_uuid, str(app)],
        check=True,
    )

    # --- Launch with KSPROJECT_TEST=1 via SIMCTL_CHILD_ prefix ---
    # simctl forwards any env var prefixed SIMCTL_CHILD_ to the launched app
    # (stripping the prefix).  -e / --setenv are not valid flags.
    launch_env = {**os.environ, "SIMCTL_CHILD_KSPROJECT_TEST": "1"}
    launch = subprocess.Popen(
        ["xcrun", "simctl", "launch", "--console-pty", sim_uuid, bundle_id],
        env=launch_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    sentinel_result: int | None = None
    totals_seen = False
    deadline = time.monotonic() + 300
    try:
        assert launch.stdout is not None
        for line in launch.stdout:
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
        subprocess.run(["xcrun", "simctl", "terminate", sim_uuid, bundle_id],
                       check=False, capture_output=True)
        launch.terminate()

    assert sentinel_result is not None, (
        "App exited without printing KSPROJECT_TEST_RESULT sentinel "
        "(check stdout above for crash or import errors)"
    )
    assert sentinel_result == 0, "In-app tests FAILED (see app output above)"

