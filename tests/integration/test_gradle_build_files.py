"""Hermetic tests for the gradle build-file generators and toolchain discovery.

We avoid invoking ``GradleProjectBuilder.generate()`` because that calls
``AndroidToolchain.resolve()`` which downloads cmdline-tools / SDK / NDK on
first run. Instead we exercise the individual writers and discovery helpers,
which is enough to catch the regressions Phase 3 cares about.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ksproject_utils.gradle.android_toolchain import (
    DEFAULT_API_VERSION,
    DEFAULT_NDK_VERSION,
    DEFAULT_SDK_VERSION,
    AndroidToolchain,
)
from ksproject_utils.gradle.gradle_build_files import GradleBuildFiles
from ksproject_utils.pyproject_toml import KivySchoolData


Arch = KivySchoolData.AndroidData.Arch


@pytest.fixture(autouse=True)
def _clean_android_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT", "ANDROID_NDK_ROOT", "JAVA_HOME"):
        monkeypatch.delenv(var, raising=False)


def test_root_gradle_files_written(tmp_path: Path) -> None:
    GradleBuildFiles.write_root_build_gradle(tmp_path)
    GradleBuildFiles.write_settings_gradle(tmp_path, "MinimalApp")
    GradleBuildFiles.write_gradle_properties(tmp_path)
    GradleBuildFiles.write_local_properties(tmp_path, "/some/sdk")

    assert (tmp_path / "build.gradle.kts").is_file()
    assert (tmp_path / "settings.gradle.kts").is_file()
    assert (tmp_path / "gradle.properties").is_file()
    assert (tmp_path / "local.properties").read_text().startswith("sdk.dir=/some/sdk")
    assert 'rootProject.name = "MinimalApp"' in (tmp_path / "settings.gradle.kts").read_text()


def test_app_build_gradle_contains_archs_and_sdk(tmp_path: Path) -> None:
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    GradleBuildFiles.write_app_build_gradle(
        app_dir,
        package_name="org.example.minimal_app",
        archs=[Arch.ARM64_V8A, Arch.X86_64],
        compile_sdk=DEFAULT_API_VERSION,
        min_sdk=24,
        target_sdk=DEFAULT_API_VERSION,
        ndk_version=DEFAULT_NDK_VERSION,
        ndk_path="/tmp/ndk",
    )
    text = (app_dir / "build.gradle.kts").read_text()
    assert 'namespace = "org.example.minimal_app"' in text
    assert "arm64-v8a" in text
    assert "x86_64" in text
    assert f"compileSdk = {DEFAULT_API_VERSION}" in text
    assert f'ndkVersion = "{DEFAULT_NDK_VERSION}"' in text


def test_find_ndk_picks_default_version_from_fake_kivyschool(
    tmp_project: Path, fake_kivyschool: Path
) -> None:
    a = KivySchoolData.AndroidData({"package_name": "x"})
    ndk = AndroidToolchain.find_ndk_path(a, tmp_project)
    assert ndk is not None
    assert Path(ndk) == fake_kivyschool / "android-sdk" / "ndk" / DEFAULT_NDK_VERSION


def test_find_ndk_picks_user_specified_short_form(
    tmp_project: Path, fake_kivyschool: Path
) -> None:
    a = KivySchoolData.AndroidData({"package_name": "x", "ndk": "28c"})
    ndk = AndroidToolchain.find_ndk_path(a, tmp_project)
    assert ndk is not None
    assert Path(ndk).name == DEFAULT_NDK_VERSION  # "28c" -> 28.2.13676358


def test_find_sdk_finds_platform_dir(
    tmp_project: Path, fake_kivyschool: Path
) -> None:
    """Ensure the fake_kivyschool fixture matches what ksproject expects."""
    a = KivySchoolData.AndroidData({"package_name": "x"})
    sdk = AndroidToolchain.find_sdk_path(a, tmp_project)
    assert sdk is not None
    platform_dir = Path(sdk) / "platforms" / f"android-{DEFAULT_SDK_VERSION}"
    assert platform_dir.is_dir(), (
        f"Default SDK version mismatch: fixture must contain {platform_dir}"
    )
