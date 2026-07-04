"""High-level XcodeGen/xcodebuild project orchestrator.

Mirrors ``gradle_project.GradleProject`` for the Apple side.
"""
from __future__ import annotations

import json
import platform
import plistlib
import subprocess
from pathlib import Path
from os import environ

from ..pip_install import PipInstaller
from ..platforms import IOSArm64Platform, IOSSim_Arm64Platform, IOSSim_X86_64Platform, MacOSPlatform, MacOSArm64Platform, MacOSX86_64Platform
from ..pyproject_toml import PyProjectToml
from .github_actions import write_appstore_workflow
from .python_apple import copy_site_frameworks
#from .xcode_project_builder import XcodeProjectBuilder
from ..pyproject_toml import KivySchoolData
from .xcodegen_runner import XcodeGenRunner
from .python_apple import (
    DEFAULT_APPLE_PY_VERSION,
    PY_VERSION,
    ApplePythonFramework,
    apple_python_cache_root,
    unsupported_apple_py_error,
)
from ..python_version import read_python_version_pin

from ksp_bootstraps.bootstrap import BootstrapProtocol
from ksp_bootstraps.bootstraps import get_bootstrap

class XcodeProjectError(Exception):
    pass

#AppleData = KivySchoolData.MacosData | KivySchoolData.IosData
AppleData = KivySchoolData.AppleData

class XcodeProjectDelegate:
    working_dir: Path
    xcode_dir: Path
    data: AppleData
    #macos_data: KivySchoolData.MacosData
    #bootstrap: BootstrapProtocol
    toolchain: XcodeGenRunner

    def __init__(self, working_dir: Path, xcode_dir: Path, data: AppleData, toolchain: XcodeGenRunner) -> None:
        self.working_dir = working_dir
        self.xcode_dir = xcode_dir
        self.data = data
        self.toolchain = toolchain
        self.py_pin = read_python_version_pin(working_dir)

    def install_cpython(self):
        data = self.data
        toolchain = self.toolchain
        framework = ApplePythonFramework(
            apple_python_cache_root(),
            version=self.py_pin.resolve(DEFAULT_APPLE_PY_VERSION),
        )
        # Fail fast on a .python-version pin BeeWare doesn't ship, before
        # any downloads or project generation happen.
        if framework.framework is None:
            raise unsupported_apple_py_error(framework.version)
        framework.install_to(self.xcode_dir / "Frameworks")
        # install_cpython_android(
        #     data.kivyschool_root(self.working_dir),
        #     [arch.value for arch in data.archs],
        #     toolchain.sdk_path,
        #     toolchain.ndk_path,
        #     toolchain.java_path
        # )

    def xcode_generate(self, **kw):
        self.toolchain.generate(**kw)

    

    @property
    def py_version(self) -> str:
        return self.py_pin.major_minor_or(PY_VERSION)

    @property
    def uv_py_version(self) -> str:
        """Exact version for `uv run --python` pins in generated scripts."""
        return self.py_pin.full_or(self.py_version)

class XcodeProject:

    #builder: XcodeProjectBuilder
    bootstrap: BootstrapProtocol
    delegate: XcodeProjectDelegate

    def __init__(self, project_path: Path):
        project_path = Path(project_path).resolve()
        if not (project_path / "pyproject.toml").is_file():
            raise XcodeProjectError(
                f"No pyproject.toml found at {project_path}"
            )
        self.project_path = project_path
        self.pyproject = PyProjectToml(str(project_path / "pyproject.toml"))
        kivy_school = self.pyproject.tool.kivy_school
        if kivy_school is None:
            raise XcodeProjectError(
                "[tool.kivy-school] section is missing in pyproject.toml"
            )
        apple_data = kivy_school.apple
        if apple_data is None:
            raise XcodeProjectError(
                "[tool.kivy-school.macos] section is missing in pyproject.toml"
            )
        
        #self.builder = XcodeProjectBuilder(self.pyproject, project_path)
        delegate = XcodeProjectDelegate(
            project_path,
            self.xcode_dir,
            apple_data,
            XcodeGenRunner()
        )
        self.delegate = delegate
        self.bootstrap = get_bootstrap(
            kivy_school.bootstrap,
            self.pyproject,
            delegate
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def app_name(self) -> str:
        ks = self.pyproject.tool.kivy_school
        if ks and ks.app_name:
            return ks.app_name
        raise Exception("tool.kivy-school.app_name is missing")

    @property
    def xcode_dir(self) -> Path:
        return self.project_path / "project_dist" / "xcode"


    @property
    def xcodeproj(self) -> Path:
        return self.xcode_dir / f"{self.app_name}.xcodeproj"

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, platforms: list[str] | None = None) -> Path:
        result = self.bootstrap.generate(platform="apple",platforms=platforms)
        if result: 
            return result
        else:
            raise Exception("bootstrap didnt return xcode path")

    def open_in_xcode(self) -> None:
        subprocess.run(["open", str(self.xcodeproj)], check=False)

    def install_frameworks(self):

        self.bootstrap.install_frameworks()

    def install_site_packages(
        self, platforms: list[str], simulator: bool = False
    ) -> None:
        """Pip-install the project into per-platform site_packages dirs.

        After installing, move any ``.frameworks/`` dropped by the kivy wheel
        into ``Support/`` and clean them out of every site_packages slice.
        """
        platform_classes = []
        if "iOS" in platforms:
            if simulator:
                arch = platform.machine()  # 'arm64' on Apple Silicon, 'x86_64' on Intel
                if arch == "arm64":
                    platform_classes.append(IOSSim_Arm64Platform)
                else:
                    platform_classes.append(IOSSim_X86_64Platform)
            else:
                platform_classes.append(IOSArm64Platform)
        if "macOS" in platforms:
            arch = platform.machine()  # 'arm64' on Apple Silicon, 'x86_64' on Intel
            if arch == "arm64":
                platform_classes.append(MacOSArm64Platform)
            else:
                platform_classes.append(MacOSX86_64Platform)

        for cls in platform_classes:
            plat = cls(str(self.project_path))
            site = plat.site_packages
            Path(plat.site_packages).mkdir(parents=True, exist_ok=True)
            PipInstaller.install(
                uv_src=str(self.project_path),
                platform=plat,
                site_packages=site,
            )

            if not isinstance(plat, MacOSPlatform):
                ios_module = Path(site) / "ios.py"
                if not ios_module.exists():
                    ios_module.write_bytes(
                        (Path(__file__).parent / "templates" / "ios.file").read_bytes()
                    )



        copy_site_frameworks(
            self.xcode_dir / "Frameworks",
            self.xcode_dir / "site_packages",
        )

    # ------------------------------------------------------------------
    # Build via xcodebuild
    # ------------------------------------------------------------------

    @staticmethod
    def _configuration(variant: str) -> str:
        if variant == "debug":
            return "Debug"
        if variant == "release":
            return "Release"
        raise XcodeProjectError(
            f"Unknown variant {variant!r}; expected 'debug' or 'release'"
        )

    def _xcodebuild(self, destination: str, variant: str) -> Path:
        if not self.xcodeproj.exists():
            raise XcodeProjectError(
                f"Xcode project not generated yet: {self.xcodeproj} missing. "
                "Run `ksproject ios build` (or `macos build`) first."
            )
        config = self._configuration(variant)
        derived = self.xcode_dir / "build"
        cmd = [
            "xcodebuild",
            "-project", str(self.xcodeproj),
            "-scheme", self.app_name,
            "-configuration", config,
            "-destination", destination,
            "-derivedDataPath", str(derived),
            "-skipPackagePluginValidation",
            "-skipMacroValidation",
            "build",
        ]
        result = subprocess.run(cmd, cwd=self.xcode_dir, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise XcodeProjectError(
                f"xcodebuild exited with code {result.returncode}"
            )
        # Locate the .app inside derivedData for the sdk we just built.
        if "iOS Simulator" in destination:
            sdk = "iphonesimulator"
        elif "iOS" in destination:
            sdk = "iphoneos"
        else:
            sdk = "macos"
        return self._find_app(sdk=sdk)

    @staticmethod
    def _app_sdk(app: Path) -> str:
        # Products subdir looks like "Debug-iphoneos", "Release-iphonesimulator"
        # or plain "Debug"/"Release" for macOS.
        name = app.parent.name
        if name.endswith("-iphonesimulator"):
            return "iphonesimulator"
        if name.endswith("-iphoneos"):
            return "iphoneos"
        return "macos"

    def _find_app(self, sdk: str | None = None) -> Path:
        products = self.xcode_dir / "build" / "Build" / "Products"
        candidates = sorted(products.rglob(f"{self.app_name}.app"))
        if sdk is not None:
            candidates = [c for c in candidates if self._app_sdk(c) == sdk]
        if not candidates:
            where = f" for {sdk}" if sdk else ""
            raise XcodeProjectError(
                f"No {self.app_name}.app found{where} under {products}. "
                "Run the matching build first."
            )
        return candidates[-1]
    

    def ios_build(self, variant: str = "debug", simulator: bool = False) -> Path:
        
        platforms = ["iOS", "macOS"]
        just_created = not self.xcodeproj.exists()
        if just_created:
            #raise Exception()
            self.generate(platforms=platforms)
            self.open_in_xcode()
        self.bootstrap.install_frameworks()
        kivy_school = self.pyproject.tool.kivy_school
        if kivy_school:
            apple = kivy_school.apple
            if apple:
                self.platform_pre_build_script(apple.ios)
        self.install_site_packages(platforms=["iOS"], simulator=simulator)
        self.bootstrap.sync_site_xcframeworks()
        dest = (
            "generic/platform=iOS Simulator"
            if simulator
            else "generic/platform=iOS"
        )
        return self._xcodebuild(dest, variant)
    

    def macos_build(self, variant: str = "debug") -> Path:
        platforms = ["iOS", "macOS"]
        just_created = not self.xcodeproj.exists()
        if just_created:
            self.generate(platforms=platforms)
            self.open_in_xcode()
        self.bootstrap.install_frameworks()
        kivy_school = self.pyproject.tool.kivy_school
        if kivy_school:
            apple = kivy_school.apple
            if apple:
                self.platform_pre_build_script(apple.macos) # type: ignore
        self.install_site_packages(platforms=["iOS", "macOS"])
        return self._xcodebuild("generic/platform=macOS", variant)

    # ------------------------------------------------------------------
    # Archive / App Store Connect upload
    # ------------------------------------------------------------------

    def _xcarchive(self, destination: str, variant: str, sdk: str) -> Path:
        if not self.xcodeproj.exists():
            raise XcodeProjectError(
                f"Xcode project not generated yet: {self.xcodeproj} missing. "
                "Run a build first."
            )
        config = self._configuration(variant)
        derived = self.xcode_dir / "build"
        archive_path = self.xcode_dir / "archives" / f"{self.app_name}-{sdk}.xcarchive"
        cmd = [
            "xcodebuild", "archive",
            "-project", str(self.xcodeproj),
            "-scheme", self.app_name,
            "-configuration", config,
            "-destination", destination,
            "-archivePath", str(archive_path),
            "-derivedDataPath", str(derived),
            "-allowProvisioningUpdates",
            "-skipPackagePluginValidation",
            "-skipMacroValidation",
        ]
        result = subprocess.run(cmd, cwd=self.xcode_dir, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise XcodeProjectError(
                f"xcodebuild archive exited with code {result.returncode}"
            )
        return archive_path

    def _export_upload(
        self,
        archive_path: Path,
        team: str | None,
        key_id: str,
        issuer_id: str,
        key_path: Path,
    ) -> None:
        export_dir = self.xcode_dir / "export"
        opts: dict = {
            "method": "app-store-connect",
            "destination": "upload",
        }
        if team:
            opts["teamID"] = team
        opts_path = self.xcode_dir / "ExportOptions.plist"
        with open(opts_path, "wb") as f:
            plistlib.dump(opts, f)
        cmd = [
            "xcodebuild", "-exportArchive",
            "-archivePath", str(archive_path),
            "-exportOptionsPlist", str(opts_path),
            "-exportPath", str(export_dir),
            "-allowProvisioningUpdates",
            "-authenticationKeyID", key_id,
            "-authenticationKeyIssuerID", issuer_id,
            "-authenticationKeyPath", str(key_path),
        ]
        result = subprocess.run(cmd, cwd=self.xcode_dir, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise XcodeProjectError(
                f"xcodebuild -exportArchive (upload) exited with code {result.returncode}"
            )

    def _resolve_upload_creds(
        self,
        key_id: str | None,
        issuer_id: str | None,
        key_path: str | None,
    ) -> tuple[str, str, Path]:
        key_id = key_id or environ.get("ASC_KEY_ID")
        issuer_id = issuer_id or environ.get("ASC_ISSUER_ID")
        key_path = key_path or environ.get("ASC_KEY_PATH")
        missing = [
            name
            for name, val in (
                ("--asc-key-id / ASC_KEY_ID", key_id),
                ("--asc-issuer-id / ASC_ISSUER_ID", issuer_id),
                ("--asc-key-path / ASC_KEY_PATH", key_path),
            )
            if not val
        ]
        if missing:
            raise XcodeProjectError(
                "App Store Connect upload requires: " + ", ".join(missing)
            )
        p8 = Path(key_path).expanduser()  # type: ignore[arg-type]
        if not p8.is_file():
            raise XcodeProjectError(f"App Store Connect key file not found: {p8}")
        return key_id, issuer_id, p8  # type: ignore[return-value]

    def _stamp_bundle_versions(
        self, build_number: str | None, app_version: str | None
    ) -> None:
        """Rewrite CFBundleVersion / CFBundleShortVersionString in the
        generated app Info.plist so every upload gets a unique build number."""
        if build_number is None and app_version is None:
            return
        info_plist = self.xcode_dir / "Sources" / "Info.plist"
        if not info_plist.is_file():
            raise XcodeProjectError(
                f"App Info.plist not found: {info_plist}. Generate the "
                "Xcode project first."
            )
        with open(info_plist, "rb") as f:
            props = plistlib.load(f)
        if build_number is not None:
            props["CFBundleVersion"] = build_number
        if app_version is not None:
            props["CFBundleShortVersionString"] = app_version
        with open(info_plist, "wb") as f:
            plistlib.dump(props, f)
        print(
            f"Stamped {info_plist.name}: "
            f"version={props.get('CFBundleShortVersionString')} "
            f"build={props.get('CFBundleVersion')}"
        )

    def _archive(
        self,
        *,
        platform_data: object,
        install_platforms: list[str],
        destination: str,
        sdk: str,
        team: str | None,
        variant: str,
        upload: bool,
        key_id: str | None,
        issuer_id: str | None,
        key_path: str | None,
        build_number: str | None = None,
        app_version: str | None = None,
    ) -> Path:
        # Resolve upload credentials up front so we fail before the long build.
        creds = (
            self._resolve_upload_creds(key_id, issuer_id, key_path)
            if upload
            else None
        )
        if upload and not team:
            raise XcodeProjectError(
                "App Store archive needs a developer_team set in "
                "[tool.kivy-school.ios]/[tool.kivy-school.macos]."
            )
        just_created = not self.xcodeproj.exists()
        if just_created:
            self.generate(platforms=["iOS", "macOS"])
            self.open_in_xcode()
        self.bootstrap.install_frameworks()
        self.platform_pre_build_script(platform_data)
        self.install_site_packages(platforms=install_platforms)
        self.bootstrap.sync_site_xcframeworks()
        self._stamp_bundle_versions(build_number, app_version)
        archive_path = self._xcarchive(destination, variant, sdk)
        if upload:
            assert creds is not None
            self._export_upload(archive_path, team, *creds)
        return archive_path

    def ios_archive(
        self,
        variant: str = "release",
        upload: bool = False,
        key_id: str | None = None,
        issuer_id: str | None = None,
        key_path: str | None = None,
        build_number: str | None = None,
        app_version: str | None = None,
    ) -> Path:
        apple = self.pyproject.tool.kivy_school.apple  # type: ignore[union-attr]
        ios = apple.ios if apple else None
        return self._archive(
            platform_data=ios,
            install_platforms=["iOS"],
            destination="generic/platform=iOS",
            sdk="ios",
            team=ios.developer_team if ios else None,
            variant=variant,
            upload=upload,
            key_id=key_id,
            issuer_id=issuer_id,
            key_path=key_path,
            build_number=build_number,
            app_version=app_version,
        )

    def macos_archive(
        self,
        variant: str = "release",
        upload: bool = False,
        key_id: str | None = None,
        issuer_id: str | None = None,
        key_path: str | None = None,
        build_number: str | None = None,
        app_version: str | None = None,
    ) -> Path:
        apple = self.pyproject.tool.kivy_school.apple  # type: ignore[union-attr]
        macos = apple.macos if apple else None
        return self._archive(
            platform_data=macos,
            install_platforms=["iOS", "macOS"],
            destination="generic/platform=macOS",
            sdk="macos",
            team=macos.developer_team if macos else None,
            variant=variant,
            upload=upload,
            key_id=key_id,
            issuer_id=issuer_id,
            key_path=key_path,
            build_number=build_number,
            app_version=app_version,
        )

    def create_action(self, platform: str) -> Path:
        """Write a tag-triggered App Store upload workflow for ``platform``."""
        return write_appstore_workflow(self.project_path, platform)

    def platform_pre_build_script(self, data: object):
        
        if not hasattr(data, "pre_build"): return
        
        env = {**environ}

        script: Path | None = getattr(data, "pre_build")
        if script:
            cur = Path.cwd()
            env["WHEELHOUSE"] = f"{cur / "wheelhouse"}"
            match script.suffix:
                case ".py":
                    subprocess.run(
                        ["uv", "run", str(script.absolute())],
                        check=True,
                        env=env
                    )
                case _:
                    subprocess.run(
                        [str(script.absolute())],
                        check=True,
                        env=env
                    )

    # ------------------------------------------------------------------
    # Devices (iOS only — simctl + devicectl)
    # ------------------------------------------------------------------

    def devices(self) -> list[dict]:
        items: list[dict] = []
        items.extend(self._list_simulators())
        items.extend(self._list_physical_devices())
        return items

    def _list_simulators(self) -> list[dict]:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "--json", "devices", "available"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        out: list[dict] = []
        for runtime, devs in (data.get("devices") or {}).items():
            for d in devs:
                out.append({
                    "kind": "simulator",
                    "uuid": d.get("udid", ""),
                    "name": d.get("name", ""),
                    "state": d.get("state", ""),
                    "runtime": runtime,
                })
        return out

    def _list_physical_devices(self) -> list[dict]:
        try:
            result = subprocess.run(
                ["xcrun", "devicectl", "list", "devices", "--json-output", "-"],
                capture_output=True, text=True, timeout=10,
            )
        except subprocess.TimeoutExpired:
            return []
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        out: list[dict] = []
        for d in (data.get("result", {}).get("devices") or []):
            ident = d.get("hardwareProperties", {}).get("udid") or d.get("identifier", "")
            name = d.get("deviceProperties", {}).get("name", "")
            out.append({
                "kind": "device",
                "uuid": ident,
                "name": name,
                "state": d.get("connectionProperties", {}).get("tunnelState", ""),
            })
        return out

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def _bundle_id(self, app: Path) -> str:
        info_plist = app / "Info.plist"
        with open(info_plist, "rb") as f:
            return plistlib.load(f)["CFBundleIdentifier"]

    def ios_run(
        self,
        uuid: str | None = None,
        name: str | None = None,
    ) -> None:
        if (uuid is None) == (name is None):
            raise XcodeProjectError("ios run requires exactly one of --uuid or --name")
        if name is not None:
            target = self._find_device_by_name(name)
            uuid = target["uuid"]
            kind = target["kind"]
        else:
            target = self._find_device_by_uuid(uuid) # type: ignore
            kind = target["kind"] if target else "simulator"

        sdk = "iphonesimulator" if kind == "simulator" else "iphoneos"
        app = self._find_app(sdk=sdk)
        bundle_id = self._bundle_id(app)
        print(f"App: {app}")
        if kind == "simulator":
            print(f"Booting simulator {uuid}...")
            subprocess.run(
                ["xcrun", "simctl", "boot", uuid], # type: ignore
                check=False, capture_output=True,
            ) # type: ignore
            print(f"Installing {app.name} (this may take ~30-60s)...")
            subprocess.run(["xcrun", "simctl", "install", uuid, str(app)], check=True) # type: ignore
            print("Launching...")
            subprocess.run(
                ["xcrun", "simctl", "launch", "--console-pty", uuid, bundle_id], # type: ignore
                check=True,
            ) # type: ignore
        else:
            subprocess.run(
                ["xcrun", "devicectl", "device", "install", "app",
                 "--device", uuid, str(app)], # type: ignore
                check=True,
            ) # type: ignore
            subprocess.run(
                ["xcrun", "devicectl", "device", "process", "launch",
                 "--console", "--device", uuid, bundle_id], # type: ignore
                check=True,
            ) # type: ignore

    def macos_run(self) -> None:
        app = self._find_app(sdk="macos")
        # Launch the executable directly (not via `open`) so the app's
        # stdout/stderr stream to this terminal.
        with open(app / "Contents" / "Info.plist", "rb") as f:
            executable = plistlib.load(f)["CFBundleExecutable"]
        subprocess.run(
            [str(app / "Contents" / "MacOS" / executable)],
            check=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_device_by_uuid(self, uuid: str) -> dict | None:
        for d in self._list_simulators():
            if d["uuid"] == uuid:
                return d
        for d in self._list_physical_devices():
            if d["uuid"] == uuid:
                return d
        return None

    def _find_device_by_name(self, name: str) -> dict:
        matches = [d for d in self.devices() if d["name"] == name]
        if not matches:
            raise XcodeProjectError(f"No simulator or device named {name!r}")
        if len(matches) > 1:
            raise XcodeProjectError(
                f"Ambiguous name {name!r}; use --uuid instead"
            )
        return matches[0]
