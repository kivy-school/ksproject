"""Unit tests for ``ksproject_utils.pyproject_toml``."""
from __future__ import annotations

from pathlib import Path

import pytest

from ksproject_utils.pyproject_toml import KivySchoolData, PyProjectToml


def test_parses_minimal_pyproject(tmp_project: Path) -> None:
    pp = PyProjectToml(str(tmp_project / "pyproject.toml"))
    assert pp.project.name == "minimal_app"
    assert pp.tool.kivy_school is not None
    ks = pp.tool.kivy_school
    assert ks.app_name == "minimal_app"
    assert ks.android is not None
    assert ks.ios is not None
    assert ks.macos is not None


def test_developer_team_defaults_to_none(tmp_project: Path) -> None:
    pp = PyProjectToml(str(tmp_project / "pyproject.toml"))
    ks = pp.tool.kivy_school
    assert ks is not None
    assert ks.ios is not None and ks.ios.developer_team is None
    assert ks.macos is not None and ks.macos.developer_team is None


def test_developer_team_parsed(tmp_project_with_team: Path) -> None:
    pp = PyProjectToml(str(tmp_project_with_team / "pyproject.toml"))
    ks = pp.tool.kivy_school
    assert ks is not None and ks.ios is not None and ks.macos is not None
    assert ks.ios.developer_team == "ABC123XYZ"
    assert ks.macos.developer_team == "ABC123XYZ"


def test_android_defaults(tmp_project: Path) -> None:
    pp = PyProjectToml(str(tmp_project / "pyproject.toml"))
    a = pp.tool.kivy_school.android
    assert a is not None
    assert a.package_name == "org.example.minimal_app"
    assert a.global_tools is True
    assert a.global_tools_path is None
    archs = [arch.value for arch in a.archs]
    assert "arm64-v8a" in archs


def test_kivyschool_root_local(tmp_project: Path) -> None:
    pp = PyProjectToml(str(tmp_project / "pyproject.toml"))
    a = pp.tool.kivy_school.android
    assert a is not None
    assert a.kivyschool_root(tmp_project) == tmp_project / ".kivyschool"


def test_kivyschool_root_global_default(tmp_path: Path) -> None:
    a = KivySchoolData.AndroidData({"package_name": "x", "global_tools": True})
    assert a.kivyschool_root(tmp_path) == Path.home() / ".kivyschool"


def test_kivyschool_root_global_path_override(tmp_path: Path) -> None:
    custom = tmp_path / "custom-tools"
    a = KivySchoolData.AndroidData(
        {
            "package_name": "x",
            "global_tools": True,
            "global_tools_path": str(custom),
        }
    )
    assert a.kivyschool_root(tmp_path) == custom
