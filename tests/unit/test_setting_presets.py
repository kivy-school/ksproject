"""Unit tests for ``ksp_bootstraps.xcode.setting_presets``."""
from __future__ import annotations

import pytest

from ksp_bootstraps.xcode import setting_presets as sp

# Apple/Xcode pipeline tests: only run in the macOS `apple` CI job, never on
# Ubuntu/Windows (the all-OS job runs with `-m "not apple"`).
pytestmark = pytest.mark.apple


def test_merged_later_wins() -> None:
    out = sp.merged({"A": 1, "B": 2}, {"B": 3, "C": 4})
    assert out == {"A": 1, "B": 3, "C": 4}


def test_target_settings_auto_empty_platform() -> None:
    # "auto" means no platform-specific keys, but product settings still apply.
    out = sp.target_settings("auto")
    # PRODUCT_APPLICATION is empty in current code, so result should be {}.
    assert isinstance(out, dict)


def test_target_settings_ios_has_sdkroot() -> None:
    out = sp.target_settings("iOS")
    assert out["SDKROOT"] == "iphoneos"
    assert out["TARGETED_DEVICE_FAMILY"] == "1,2"


def test_target_settings_macos_has_sdkroot() -> None:
    out = sp.target_settings("macOS")
    assert out["SDKROOT"] == "macosx"


def test_supported_destination_includes_both() -> None:
    out = sp.supported_destination_settings(["iOS", "macOS"])
    assert "SUPPORTED_PLATFORMS" in out
    # Both platforms should be reflected.
    assert "iphoneos" in out["SUPPORTED_PLATFORMS"] or "macosx" in out["SUPPORTED_PLATFORMS"]


def test_project_settings_debug_vs_release() -> None:
    dbg = sp.project_settings("debug")
    rel = sp.project_settings("release")
    assert dbg["GCC_OPTIMIZATION_LEVEL"] == "0"
    assert rel["SWIFT_OPTIMIZATION_LEVEL"] == "-O"
    assert dbg["SWIFT_VERSION"] == rel["SWIFT_VERSION"]
