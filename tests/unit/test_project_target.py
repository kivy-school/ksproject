"""Unit tests for ``ksproject_utils.xcode.project_target.ProjectTarget``."""
from __future__ import annotations

from ksproject_utils.xcode.project_target import ProjectTarget


def _settings_dict(target: ProjectTarget) -> dict:
    return target.to_dict()["settings"]["configs"]["Debug"]


def test_default_target_has_no_development_team() -> None:
    t = ProjectTarget(name="App", info_plist_extra={}, entitlements=None)
    s = _settings_dict(t)
    assert "DEVELOPMENT_TEAM" not in s
    assert s["CODE_SIGN_STYLE"] == "Automatic"


def test_developer_team_injected_when_set() -> None:
    t = ProjectTarget(
        name="App",
        info_plist_extra={},
        entitlements=None,
        developer_team="ABC123XYZ",
    )
    s = _settings_dict(t)
    assert s["DEVELOPMENT_TEAM"] == "ABC123XYZ"
    assert s["CODE_SIGN_STYLE"] == "Automatic"


def test_info_plist_extra_merged_into_info() -> None:
    t = ProjectTarget(
        name="App",
        info_plist_extra={"NSCameraUsageDescription": "for photos"},
        entitlements=None,
    )
    info = t.to_dict()["info"]
    assert info["properties"]["NSCameraUsageDescription"] == "for photos"
    # The base plist keys are still present.
    assert "CFBundleIdentifier" in info["properties"] or len(info["properties"]) > 1


def test_no_entitlements_when_empty() -> None:
    t = ProjectTarget(name="App", info_plist_extra={}, entitlements=None)
    d = t.to_dict()
    assert "entitlements" not in d


def test_entitlements_emitted_when_set() -> None:
    t = ProjectTarget(
        name="App",
        info_plist_extra={},
        entitlements={"com.apple.security.app-sandbox": True},
    )
    d = t.to_dict()
    assert d["entitlements"]["path"] == "App.entitlements"
    assert d["entitlements"]["properties"]["com.apple.security.app-sandbox"] is True


def test_site_xcframeworks_added_as_ios_deps() -> None:
    t = ProjectTarget(
        name="App",
        info_plist_extra={},
        entitlements=None,
        site_xcframeworks=["Pillow_iOS.xcframework"],
    )
    deps = t.to_dict()["dependencies"]
    fw_deps = [d for d in deps if d.get("framework") == "Support/Pillow_iOS.xcframework"]
    assert len(fw_deps) == 1
    assert fw_deps[0]["platformFilter"] == "iOS"


def test_targets_both_destinations() -> None:
    t = ProjectTarget(name="App", info_plist_extra={}, entitlements=None)
    d = t.to_dict()
    assert d["supportedDestinations"] == ["iOS", "macOS"]
    assert d["platform"] == "auto"
