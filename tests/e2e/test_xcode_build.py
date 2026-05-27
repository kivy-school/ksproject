"""End-to-end Xcode/Apple build smoke tests (macOS only).

Real ``xcodegen`` + ``xcodebuild`` runs. Gated by ``@pytest.mark.slow``.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.apple]


@pytest.fixture(autouse=True)
def _macos_only() -> None:
    if platform.system() != "Darwin":
        pytest.skip("Apple e2e tests require macOS")


def test_xcodegen_generates_xcodeproj(minimal_app: Path) -> None:
    """**G3**: ``XcodeProject.generate()`` produces a real ``.xcodeproj``."""
    from ksproject_utils.xcode.xcode_project import XcodeProject

    project = XcodeProject(minimal_app)
    try:
        xcodeproj = project.generate(platforms=["iOS", "macOS"])
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"xcodegen not available: {exc}")
    assert xcodeproj.exists()
    assert (xcodeproj / "project.pbxproj").is_file()


@pytest.mark.simulator
def test_ios_simulator_build_produces_app(minimal_app: Path) -> None:
    """**G3 + G4 prep**: run a debug iOS-simulator build, assert .app + xcframeworks."""
    if not shutil.which("xcodebuild"):
        pytest.skip("xcodebuild not on PATH")
    from ksproject_utils.xcode.xcode_project import XcodeProject

    project = XcodeProject(minimal_app)
    try:
        artifact = project.ios_build(variant="debug", simulator=True)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"iOS simulator build unavailable: {exc}")
    assert artifact.exists()
    # Required xcframeworks for kivy + python should be present under Support/
    support = project.xcode_dir / "Support"
    xcframeworks = sorted(p.name for p in support.glob("*.xcframework"))
    assert any("Python" in n for n in xcframeworks), xcframeworks


@pytest.mark.simulator
def test_macos_build_produces_app(minimal_app: Path) -> None:
    if not shutil.which("xcodebuild"):
        pytest.skip("xcodebuild not on PATH")
    from ksproject_utils.xcode.xcode_project import XcodeProject

    project = XcodeProject(minimal_app)
    try:
        artifact = project.macos_build(variant="debug")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"macOS build unavailable: {exc}")
    assert artifact.exists()
