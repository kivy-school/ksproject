"""Apple build tests — use XcodeProject directly (no CLI subprocess).

macOS only. Downloads xcframeworks on first run (ksproject manages that).

iOS entry-point note
--------------------
ksproject writes ``project_dist/xcode/app/__main__.py`` from a template that
calls ``{module}.main()`` directly, bypassing the KSPROJECT_TEST check that
lives in ``src/{module}/__main__.py``.  To run the in-app test suite we
pre-create ``app/__main__.py`` with the test-mode branch *before* ios_build()
runs; ksproject's _write_app() skips writing if the file already exists, so
normal app usage is never affected.
"""
from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from ksproject_utils.xcode.xcode_project import XcodeProject

pytestmark = pytest.mark.apple


def _clear_deps(app_dir: Path) -> None:
    """Strip [project] dependencies before iOS build.

    ksproject provides kivy (and other native libs) via xcframeworks, not as
    pip packages.  Kivy has no ios-simulator wheel on PyPI, so leaving it in
    dependencies causes PipInstallError when building for iOS simulator.
    """
    pyproject = app_dir / "pyproject.toml"
    text = pyproject.read_text()
    text = re.sub(
        r'^(dependencies\s*=\s*\[)[^\]]*(\])',
        r'\1\2',
        text,
        flags=re.DOTALL | re.MULTILINE,
    )
    pyproject.write_text(text)


@pytest.fixture(autouse=True)
def _macos_only() -> None:
    if platform.system() != "Darwin":
        pytest.skip("Apple tests require macOS")


def test_ios_simulator_build_produces_app(minimal_app: Path) -> None:
    """ios_build(simulator=True) exits cleanly and returns an existing .app."""
    _clear_deps(minimal_app)
    project = XcodeProject(minimal_app)
    app = project.ios_build(simulator=True)
    assert app.exists(), f".app not found: {app}"


def test_ios_simulator_unittests_pass(minimal_app: Path) -> None:
    """Build with a test-mode entry point, boot a simulator, launch with
    KSPROJECT_TEST=1, and assert the in-app suite prints a PASS sentinel."""
    _clear_deps(minimal_app)
    project = XcodeProject(minimal_app)
    module = project.builder.module_name

    # --- Inject test-mode entry point before ios_build() generates the file ---
    # ksproject's _write_app() skips writing if app/__main__.py already exists.
    # We pre-create it with a KSPROJECT_TEST=1 branch; normal builds (where this
    # file doesn't pre-exist) get the plain ``module.main()`` template instead.
    app_entry = project.builder.project_dir / "app" / "__main__.py"
    app_entry.parent.mkdir(parents=True, exist_ok=True)
    app_entry.write_text(textwrap.dedent(f"""\
        import os
        import sys

        _ANDROID_MARKER = "/data/local/tmp/.ksproject_test"
        if os.environ.get("KSPROJECT_TEST") == "1" or os.path.exists(_ANDROID_MARKER):
            try:
                os.remove(_ANDROID_MARKER)
            except OSError:
                pass
            from {module}.tests.__main__ import run as _run
            sys.exit(_run())

        import {module}
        if __name__ == "__main__":
            {module}.main()
    """))

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
    # bootstatus -b blocks until the simulator finishes booting; simctl install
    # exits 16 (DeviceNotReadyError) if the simulator is still booting.
    subprocess.run(
        ["xcrun", "simctl", "bootstatus", sim_uuid, "-b"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["xcrun", "simctl", "install", sim_uuid, str(app)],
        check=True,
    )

    # --- Launch with KSPROJECT_TEST=1 via SIMCTL_CHILD_ prefix ---
    # simctl strips the SIMCTL_CHILD_ prefix and sets the var in the child
    # process.  Our injected app/__main__.py checks os.environ["KSPROJECT_TEST"].
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
        subprocess.run(
            ["xcrun", "simctl", "terminate", sim_uuid, bundle_id],
            check=False, capture_output=True,
        )
        launch.terminate()

    assert sentinel_result is not None, (
        "App exited without printing KSPROJECT_TEST_RESULT sentinel "
        "(check stdout above for crash or import errors)"
    )
    assert sentinel_result == 0, "In-app tests FAILED (see app output above)"
