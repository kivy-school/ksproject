"""Orchestrates XcodeGen project generation.

Ports ``PSProject/Sources/XcodeProjectBuilder/XcodeProjectBuilder.swift`` and
``XcodeProjectBuilder+folders.swift``.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..pyproject_toml import PyProjectToml
from .main_files import render_main_swift
from .plist_templates import STDLIB_PLIST_XML
from .project_spec import ProjectSpec
from .project_target import ProjectTarget
from .python_apple import ApplePythonFramework, apple_python_cache_root
from .static_templates import (
    APP_ICON_CONTENTS,
    APP_MAIN_PY_TEMPLATE,
    ASSETS_CATALOG_CONTENTS,
    LAUNCH_SCREEN_STORYBOARD,
)
from .xcodegen_runner import XcodeGenRunner
from ksproject_utils.tools import resolve_module_name

class XcodeProjectBuilderError(Exception):
    pass


class XcodeProjectBuilder:
    """Materializes ``project_dist/xcode/`` and runs ``xcodegen``."""

    def __init__(self, pyproject: PyProjectToml, working_dir: Path) -> None:
        self.pyproject = pyproject
        self.working_dir = working_dir

        kivy_school = pyproject.tool.kivy_school
        if kivy_school is None:
            raise XcodeProjectBuilderError(
                "[tool.kivy-school] is missing in pyproject.toml"
            )
        self.kivy_school = kivy_school
        self.app_name = kivy_school.app_name or pyproject.project.name
        self.module_name = resolve_module_name(self.pyproject.project.name)
        # project_name = (
        #     self.pyproject.project.name.strip().replace("-", "_").replace(" ", "_")
        # )
        ios = kivy_school.ios
        macos = kivy_school.macos
        if ios is not None:
            self.bundle_id_prefix = self._prefix_from_bundle_id(ios.bundle_id)
        elif macos is not None:
            self.bundle_id_prefix = self._prefix_from_bundle_id(macos.bundle_id)
        else:
            self.bundle_id_prefix = f"org.kivyschool"

        info_plist_extra: dict = {}
        self.info_plist_extra = info_plist_extra
        self.entitlements: dict = {}
        self.developer_team: str | None = None
        if ios is not None:
            info_plist_extra.update(ios.info_plist)
            self.entitlements.update(ios.entitlements)
            if ios.developer_team:
                self.developer_team = ios.developer_team
        if macos is not None:
            # macOS keys win when both are present (entitlements typically diverge).
            info_plist_extra.update(macos.info_plist)
            self.entitlements.update(macos.entitlements)
            if macos.developer_team:
                self.developer_team = macos.developer_team

        info_plist_extra["AppModule"] = self.module_name


    @staticmethod
    def _prefix_from_bundle_id(bundle_id: str) -> str:
        """``org.example.myapp`` → ``org.example``."""
        parts = bundle_id.rsplit(".", 1)
        return parts[0] if len(parts) == 2 else bundle_id

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    @property
    def project_dir(self) -> Path:
        return self.working_dir / "project_dist" / "xcode"

    # ------------------------------------------------------------------
    # Folder layout
    # ------------------------------------------------------------------

    def _create_root_folders(self) -> None:
        for sub in (
            "Sources/IphoneOS",
            "Sources/MacOS",
            "Sources/Shared",
            "Resources",
            "Resources/Images.xcassets",
            "Resources/Images.xcassets/AppIcon.appiconset",
            "Frameworks",
            "app",
            "site_packages/iphoneos",
            "site_packages/iphonesimulator",
            "site_packages/macos",
        ):
            (self.project_dir / sub).mkdir(parents=True, exist_ok=True)

    def _write_resources(self) -> None:
        (self.project_dir / "Resources/Images.xcassets/Contents.json").write_text(
            ASSETS_CATALOG_CONTENTS
        )
        (
            self.project_dir
            / "Resources/Images.xcassets/AppIcon.appiconset/Contents.json"
        ).write_text(APP_ICON_CONTENTS)
        launch = self.project_dir / "Resources/Launch Screen.storyboard"
        if not launch.exists():
            launch.write_text(LAUNCH_SCREEN_STORYBOARD)

    def _write_support(self) -> None:
        plist = self.project_dir / "Frameworks/dylib-Info-template.plist"
        plist.write_text(STDLIB_PLIST_XML)

    def _write_sources(self) -> None:
        ios_main = self.project_dir / "Sources/IphoneOS/main.swift"
        if not ios_main.exists():
            ios_main.write_text(render_main_swift("iOS"))
        macos_main = self.project_dir / "Sources/MacOS/main.swift"
        if not macos_main.exists():
            macos_main.write_text(render_main_swift("macOS"))
        kivylauncher_src = Path(__file__).parent / "templates" / "KivyLauncher.swift"
        shared_kl = self.project_dir / "Sources/Shared/KivyLauncher.swift"
        if not shared_kl.exists():
            code = kivylauncher_src.read_bytes()
            shared_kl.write_bytes(code)
        

    def _write_app(self) -> None:
        app_dir = self.project_dir / "app"
        old = app_dir / "main.py"
        if old.exists():
            old.unlink()
        entry = app_dir / "__main__.py"
        if not entry.exists():
            entry.write_text(APP_MAIN_PY_TEMPLATE.format(module_name=self.module_name))

    def _install_frameworks(self) -> None:
        self._write_support()  # ensure dylib-Info-template.plist exists for XcodeGen validation
        ApplePythonFramework(apple_python_cache_root()).install_to(self.project_dir / "Frameworks")
        # if "iOS" in platforms:
        #     fetch_kivy_sdl2_xcframeworks(self.project_dir / "Frameworks")  # TEMPORARY: remove once kivy2x ships .frameworks/

    # ------------------------------------------------------------------
    # Spec + xcodegen
    # ------------------------------------------------------------------

    def _build_spec(self) -> dict:
        support = self.project_dir / "Frameworks"
        site_xcframeworks = sorted(
            p.name for p in support.iterdir()
            if p.is_dir() and p.suffix == ".xcframework"
        ) if support.is_dir() else []
        target = ProjectTarget(
            name=self.app_name,
            info_plist_extra=self.info_plist_extra,
            entitlements=self.entitlements if self.entitlements else None,
            site_xcframeworks=site_xcframeworks,
            developer_team=self.developer_team,
        )
        spec = ProjectSpec(
            name=self.app_name,
            bundle_id_prefix=self.bundle_id_prefix,
            target=target,
        )
        return spec.to_dict()

    def _write_spec(self) -> Path:
        spec_path = self.project_dir / "project.yml"
        with spec_path.open("w") as f:
            yaml.safe_dump(self._build_spec(), f, sort_keys=False)
        return spec_path

    def sync_site_xcframeworks(self) -> None:
        """Sync Support/*.xcframework into the Xcode project.

        Compares what is physically present in Support/ against what is
        currently in project.yml.  If the sets differ (new xcframework added
        or one removed), rewrites project.yml and re-runs XcodeGen.
        Called after pip-install + copy_site_frameworks, just before xcodebuild.
        """
        spec_path = self.project_dir / "project.yml"
        if not spec_path.exists():
            return
        new_text = yaml.safe_dump(self._build_spec(), sort_keys=False)
        if spec_path.read_text() == new_text:
            return
        print("[ksproject] xcframework list changed — regenerating Xcode project")
        spec_path.write_text(new_text)
        runner = XcodeGenRunner()
        runner.generate(spec_path=spec_path, project_dir=self.project_dir)

    def generate(self, platforms: list[str] | None = None) -> Path:
        """Scaffold the Xcode project and return the path to the .xcodeproj.

        Only creates folder layout, source files, and runs XcodeGen.
        Runtime assets (Support/ stdlib slices, xcframeworks) are handled
        separately by _install_frameworks(), which is always called by the
        build methods regardless of whether the project already exists.
        """
        plats = platforms or ["iOS", "macOS"]
        self._create_root_folders()
        self._write_resources()
        self._write_support()
        self._write_sources()
        self._write_app()
        spec_path = self._write_spec()

        runner = XcodeGenRunner()
        runner.generate(spec_path=spec_path, project_dir=self.project_dir)

        xcodeproj = self.project_dir / f"{self.app_name}.xcodeproj"
        if not xcodeproj.exists():
            raise XcodeProjectBuilderError(
                f"xcodegen succeeded but {xcodeproj} not found"
            )
        return xcodeproj
