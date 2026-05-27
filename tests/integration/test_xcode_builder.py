"""Hermetic integration tests for the Xcode project builder.

These tests exercise the full ``XcodeProject`` → ``XcodeProjectBuilder`` chain
but stop before running ``xcodegen`` itself (kept fast, no network, no Xcode).
The end-to-end test that actually runs ``xcodegen`` lives in
``tests/e2e/test_xcode_e2e.py`` and is gated by ``@pytest.mark.slow``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ksproject_utils.xcode.xcode_project_builder import XcodeProjectBuilder
from ksproject_utils.pyproject_toml import PyProjectToml


def _builder(project_path: Path) -> XcodeProjectBuilder:
    pp = PyProjectToml(str(project_path / "pyproject.toml"))
    return XcodeProjectBuilder(pp, project_path)


def test_builder_loads_minimal_project(tmp_project: Path) -> None:
    b = _builder(tmp_project)
    assert b.app_name == "minimal_app"
    assert b.bundle_id_prefix == "org.example"
    assert b.developer_team is None


def test_builder_picks_up_developer_team(tmp_project_with_team: Path) -> None:
    b = _builder(tmp_project_with_team)
    assert b.developer_team == "ABC123XYZ"


def test_spec_target_has_no_team_by_default(tmp_project: Path) -> None:
    b = _builder(tmp_project)
    spec = b._build_spec()
    settings = spec["targets"][b.app_name]["settings"]["configs"]["Debug"]
    assert "DEVELOPMENT_TEAM" not in settings


def test_spec_target_wires_developer_team(tmp_project_with_team: Path) -> None:
    b = _builder(tmp_project_with_team)
    spec = b._build_spec()
    settings = spec["targets"][b.app_name]["settings"]["configs"]["Debug"]
    assert settings["DEVELOPMENT_TEAM"] == "ABC123XYZ"


def test_spec_declares_both_destinations(tmp_project: Path) -> None:
    b = _builder(tmp_project)
    spec = b._build_spec()
    tgt = spec["targets"][b.app_name]
    assert tgt["supportedDestinations"] == ["iOS", "macOS"]
    assert tgt["platform"] == "auto"


def test_spec_contains_kivy_and_python_deps(tmp_project: Path) -> None:
    b = _builder(tmp_project)
    spec = b._build_spec()
    deps = spec["targets"][b.app_name]["dependencies"]
    packages = {d.get("package") for d in deps}
    assert "PySwiftKit" in packages
    assert "CPython" in packages
    assert "KivyLauncher" in packages
    assert "Kivy_iOS_Module" in packages


def test_folder_scaffolding(tmp_project: Path) -> None:
    """Folder + source layout should be created without invoking XcodeGen."""
    b = _builder(tmp_project)
    b._create_root_folders()
    b._write_resources()
    b._write_support()
    b._write_sources()
    b._write_app()

    root = b.project_dir
    expected = [
        "Sources/IphoneOS",
        "Sources/MacOS",
        "Sources/Shared",
        "Resources/Images.xcassets",
        "Support",
        "app",
        "site_packages/iphoneos",
        "site_packages/iphonesimulator",
        "site_packages/macos",
    ]
    for sub in expected:
        assert (root / sub).is_dir(), f"missing {sub}"

    assert (root / "Sources/Shared/main.swift").is_file()
    assert (root / "Sources/MacOS/main_macos.swift").is_file()
    assert (root / "Support/dylib-Info-template.plist").is_file()
    assert (root / "app/__main__.py").is_file()
    assert "minimal_app" in (root / "app/__main__.py").read_text()


def test_spec_yaml_writable(tmp_project: Path) -> None:
    b = _builder(tmp_project)
    b._create_root_folders()
    b._write_support()  # Support must exist for _build_spec to enumerate xcframeworks
    spec_path = b._write_spec()
    assert spec_path.is_file()
    text = spec_path.read_text()
    assert "name: minimal_app" in text
    assert "supportedDestinations:" in text
