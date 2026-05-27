"""Shared pytest fixtures for the ksproject test suite.

Fixtures here are deliberately small and explicit. Anything heavier than
writing a few files to ``tmp_path`` belongs in a marker-gated test, not a
default fixture.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from ksproject_utils.pyproject_init import PyProjectInitKeys


FIXTURES_DIR = Path(__file__).parent / "fixtures"
MINIMAL_APP_DIR = FIXTURES_DIR / "minimal_app"


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
    """Copy the bundled minimal_app fixture into ``tmp_path`` and return it."""
    dst = tmp_path / "minimal_app"
    shutil.copytree(MINIMAL_APP_DIR, dst)
    return dst


@pytest.fixture
def skip_if_not_macos() -> None:
    if sys.platform != "darwin":
        pytest.skip("macOS-only test")
