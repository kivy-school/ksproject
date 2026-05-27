"""Verify default toml from ``PyProjectInitKeys`` round-trips through ``PyProjectToml``."""
from __future__ import annotations

from pathlib import Path

from ksproject_utils.pyproject_init import PyProjectInitKeys
from ksproject_utils.pyproject_toml import PyProjectToml


def _write(tmp_path: Path, name: str) -> Path:
    keys = PyProjectInitKeys(name)
    header = (
        "[project]\n"
        f'name = "{keys.module_name}"\n'
        'version = "0.0.1"\n'
        'requires-python = ">=3.13"\n'
        "dependencies = []\n\n"
    )
    p = tmp_path / "pyproject.toml"
    p.write_text(header + keys.output())
    return p


def test_default_toml_roundtrips(tmp_path: Path) -> None:
    path = _write(tmp_path, "Hello-World")
    pp = PyProjectToml(str(path))
    ks = pp.tool.kivy_school
    assert ks is not None
    assert ks.app_name == "Hello-World"
    assert ks.android is not None
    assert ks.android.package_name == "org.example.hello_world"
    assert ks.ios is not None
    assert ks.ios.bundle_id == "org.example.hello_world"
    assert ks.macos is not None
    assert ks.macos.bundle_id == "org.example.hello_world"


def test_default_android_uses_documented_versions(tmp_path: Path) -> None:
    from ksproject_utils.gradle.android_toolchain import (
        DEFAULT_API_VERSION,
        DEFAULT_SDK_VERSION,
    )

    path = _write(tmp_path, "demo")
    pp = PyProjectToml(str(path))
    a = pp.tool.kivy_school.android
    assert a is not None
    assert a.api == DEFAULT_API_VERSION
    assert a.sdk == DEFAULT_SDK_VERSION
    assert a.ndk == "28c"
    assert a.min_api == 24
    assert a.ndk_api == 24
    assert a.global_tools is False
