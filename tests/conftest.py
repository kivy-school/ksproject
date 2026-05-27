"""Shared pytest fixtures for the ksproject test suite.

Fixtures here are deliberately small and explicit. Anything heavier than
writing a few files to ``tmp_path`` belongs in a marker-gated test, not a
default fixture.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ksproject_utils.pyproject_init import PyProjectInitKeys


def _write_minimal_pyproject(
    target: Path,
    project_name: str = "minimal_app",
    developer_team: str | None = None,
) -> Path:
    """Write a minimal but realistic pyproject.toml into ``target``.

    Uses ``PyProjectInitKeys`` so the test toml matches what ``ksproject init``
    would produce, plus the `[project]` table needed by ``PyProjectToml``.
    """
    keys = PyProjectInitKeys(project_name)
    body = keys.output()
    project_header = (
        "[project]\n"
        f'name = "{keys.module_name}"\n'
        'version = "0.0.1"\n'
        'requires-python = ">=3.13"\n'
        "dependencies = []\n\n"
    )
    if developer_team:
        body = body.replace(
            '#developer_team = "ABC123XYZ"',
            f'developer_team = "{developer_team}"',
        )
    path = target / "pyproject.toml"
    path.write_text(project_header + body)
    return path


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A tmp directory containing a minimal valid ``pyproject.toml``."""
    _write_minimal_pyproject(tmp_path)
    return tmp_path


@pytest.fixture
def tmp_project_with_team(tmp_path: Path) -> Path:
    """Same as ``tmp_project`` but with a ``developer_team`` set on ios/macos."""
    _write_minimal_pyproject(tmp_path, developer_team="ABC123XYZ")
    return tmp_path


@pytest.fixture
def fake_kivyschool(tmp_path: Path) -> Path:
    """Build a fake ``.kivyschool`` tree with stubs of the tools ksproject expects.

    Layout mirrors what ``AndroidToolchain`` and the Apple builder discover:
        <root>/android-sdk/cmdline-tools/latest/bin/sdkmanager
        <root>/android-sdk/ndk/<DEFAULT_NDK_VERSION>/source.properties
        <root>/android-sdk/platforms/android-<DEFAULT_SDK_VERSION>/
        <root>/Python.xcframework/
    """
    from ksproject_utils.gradle.android_toolchain import (
        DEFAULT_NDK_VERSION,
        DEFAULT_SDK_VERSION,
    )

    root = tmp_path / ".kivyschool"
    sdk = root / "android-sdk"
    (sdk / "cmdline-tools" / "latest" / "bin").mkdir(parents=True)
    (sdk / "cmdline-tools" / "latest" / "bin" / "sdkmanager").write_text("#!/bin/sh\nexit 0\n")
    (sdk / "ndk" / DEFAULT_NDK_VERSION).mkdir(parents=True)
    (sdk / "ndk" / DEFAULT_NDK_VERSION / "source.properties").write_text(
        f"Pkg.Revision = {DEFAULT_NDK_VERSION}\n"
    )
    (sdk / "platforms" / f"android-{DEFAULT_SDK_VERSION}").mkdir(parents=True)
    (sdk / "build-tools" / DEFAULT_SDK_VERSION).mkdir(parents=True)
    (root / "Python.xcframework").mkdir(parents=True)
    return root


@pytest.fixture
def minimal_app(tmp_path: Path) -> Path:
    """A real ksproject project created exactly as per the README:
      uv init --package minimal-app --python 3.13
      uv add kivy
      ksproject init
    """
    import subprocess

    # Resolve ksproject from the same venv that is running pytest.
    _bin = Path(sys.executable).parent
    ksproject = str(_bin / ("ksproject.exe" if sys.platform == "win32" else "ksproject"))

    subprocess.run(
        ["uv", "init", "--package", "minimal-app", "--python", "3.13"],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    )
    app_dir = tmp_path / "minimal-app"

    subprocess.run(
        ["uv", "add", "kivy"],
        cwd=app_dir, check=True, capture_output=True, text=True,
    )

    subprocess.run(
        [ksproject, "init"],
        cwd=app_dir, check=True, capture_output=True, text=True,
    )

    _write_app_tests(app_dir, "minimal_app")
    return app_dir


def _write_app_tests(app_dir: Path, module: str) -> None:
    """Write a self-contained unittest suite directly into a generated app.

    Overwrites __main__.py to branch on KSPROJECT_TEST=1 (env var, set by
    the iOS test harness via simctl --setenv) or the existence of
    /data/local/tmp/.ksproject_test (pushed via adb for Android tests).
    Prints KSPROJECT_TEST_RESULT / KSPROJECT_TEST_TOTALS sentinels so the
    host e2e tests can parse pass/fail without inspecting exit codes through
    the app launcher.
    """
    import textwrap

    tests_dir = app_dir / "src" / module / "tests"
    tests_dir.mkdir(exist_ok=True)

    (tests_dir / "__init__.py").write_text(textwrap.dedent(f"""\
        import unittest

        def load_tests(loader, standard_tests, pattern):
            suite = unittest.TestSuite()
            from {module}.tests import test_smoke, test_main_widget
            for mod in (test_smoke, test_main_widget):
                suite.addTests(loader.loadTestsFromModule(mod))
            return suite
    """))

    (tests_dir / "__main__.py").write_text(textwrap.dedent(f"""\
        import os
        import sys
        import unittest

        os.environ.setdefault("KIVY_USE_DEFAULTCONFIG", "1")
        os.environ.setdefault("KIVY_NO_ARGS", "1")

        def run() -> int:
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromName("{module}.tests")
            runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
            result = runner.run(suite)
            ok = result.wasSuccessful()
            print(f"KSPROJECT_TEST_RESULT: {{'PASS' if ok else 'FAIL'}}", flush=True)
            print(
                f"KSPROJECT_TEST_TOTALS: ran={{result.testsRun}} "
                f"failed={{len(result.failures)}} errored={{len(result.errors)}}",
                flush=True,
            )
            return 0 if ok else 1

        if __name__ == "__main__":
            sys.exit(run())
    """))

    (tests_dir / "test_smoke.py").write_text(textwrap.dedent(f"""\
        import sys
        import unittest

        class SmokeTest(unittest.TestCase):
            def test_import_kivy(self):
                import kivy  # noqa: F401

            def test_import_app(self):
                import {module}.app  # noqa: F401

            def test_platform_known(self):
                self.assertIn(sys.platform, ("linux", "darwin", "win32", "android"))
    """))

    (tests_dir / "test_main_widget.py").write_text(textwrap.dedent(f"""\
        import os
        import unittest

        os.environ.setdefault("KIVY_USE_DEFAULTCONFIG", "1")
        os.environ.setdefault("KIVY_NO_ARGS", "1")

        class MainWidgetTest(unittest.TestCase):
            def test_renders(self):
                from {module}.app import KivyIntroApp
                from kivy.base import EventLoop

                EventLoop.ensure_window()
                win = EventLoop.window
                self.assertIsNotNone(win)

                app = KivyIntroApp()
                root = app.build()
                win.clear()
                win.add_widget(root)
                for _ in range(2):
                    EventLoop.idle()
                self.assertIn(root, win.children)
                win.remove_widget(root)
    """))

    # Overwrite __main__.py: branch on KSPROJECT_TEST=1 (env, iOS simctl) or
    # /data/local/tmp/.ksproject_test marker file (pushed via adb for Android).
    _ANDROID_MARKER = "/data/local/tmp/.ksproject_test"
    (app_dir / "src" / module / "__main__.py").write_text(textwrap.dedent(f"""\
        import os
        import sys

        _ANDROID_MARKER = "{_ANDROID_MARKER}"
        if os.environ.get("KSPROJECT_TEST") == "1" or os.path.exists(_ANDROID_MARKER):
            try:
                os.remove(_ANDROID_MARKER)
            except OSError:
                pass
            from {module}.tests.__main__ import run as _run
            sys.exit(_run())
        else:
            from . import main
            if __name__ == "__main__":
                main()
    """))



@pytest.fixture
def skip_if_not_macos() -> None:
    if sys.platform != "darwin":
        pytest.skip("macOS-only test")
