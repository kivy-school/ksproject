"""Unit tests for ``AndroidToolchain.find_sdk_path`` / ``find_*`` discovery.

These tests are hermetic: they monkeypatch env vars and use the
``fake_kivyschool`` fixture so nothing touches the real filesystem outside
``tmp_path``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ksproject_utils.gradle.android_toolchain import (
    DEFAULT_NDK_VERSION,
    AndroidToolchain,
)
from ksproject_utils.pyproject_toml import KivySchoolData


def _android(**extra) -> KivySchoolData.AndroidData:
    data = {"package_name": "org.example.app"}
    data.update(extra)
    return KivySchoolData.AndroidData(data)


@pytest.fixture(autouse=True)
def _clean_android_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Don't let the developer's ANDROID_HOME leak into hermetic tests."""
    for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT", "ANDROID_NDK_ROOT", "JAVA_HOME"):
        monkeypatch.delenv(var, raising=False)


def test_find_sdk_uses_local_kivyschool(
    tmp_project: Path, fake_kivyschool: Path
) -> None:
    a = _android()
    found = AndroidToolchain.find_sdk_path(a, tmp_project)
    assert found is not None
    assert Path(found) == fake_kivyschool / "android-sdk"


def test_find_sdk_returns_none_when_missing(tmp_path: Path) -> None:
    a = _android()
    assert AndroidToolchain.find_sdk_path(a, tmp_path) is None


def test_find_sdk_prefers_env_when_global_tools(
    tmp_project: Path,
    fake_kivyschool: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_sdk = tmp_path / "envroot-sdk"
    env_sdk.mkdir()
    monkeypatch.setenv("ANDROID_HOME", str(env_sdk))
    a = _android(global_tools=True)
    found = AndroidToolchain.find_sdk_path(a, tmp_project)
    assert Path(found) == env_sdk


def test_find_sdk_ignores_env_when_not_global_tools(
    tmp_project: Path,
    fake_kivyschool: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_sdk = tmp_path / "envroot-sdk"
    env_sdk.mkdir()
    monkeypatch.setenv("ANDROID_HOME", str(env_sdk))
    a = _android()  # global_tools=False by default
    found = AndroidToolchain.find_sdk_path(a, tmp_project)
    assert Path(found) == fake_kivyschool / "android-sdk"


def test_find_sdk_explicit_path_wins_over_managed(
    tmp_project: Path, fake_kivyschool: Path, tmp_path: Path
) -> None:
    explicit = tmp_path / "explicit-sdk"
    explicit.mkdir()
    a = _android(sdk_path=str(explicit))
    found = AndroidToolchain.find_sdk_path(a, tmp_project)
    assert Path(found) == explicit


def test_kivyschool_sdk_root_resolves_to_local(tmp_path: Path) -> None:
    a = _android()
    root = AndroidToolchain.kivyschool_sdk_root(tmp_path, a)
    assert root == tmp_path / ".kivyschool" / "android-sdk"


def test_kivyschool_sdk_root_global(tmp_path: Path) -> None:
    a = _android(global_tools=True, global_tools_path=str(tmp_path / "global"))
    root = AndroidToolchain.kivyschool_sdk_root(tmp_path, a)
    assert root == tmp_path / "global" / "android-sdk"
