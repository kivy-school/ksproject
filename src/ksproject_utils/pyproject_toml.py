from enum import Enum, StrEnum
from pathlib import Path

import toml

class KivySchoolData:

    app_name: str | None
    # ios: "KivySchoolData.IosData | None"
    # macos: "KivySchoolData.MacosData | None"
    android: "KivySchoolData.AndroidData | None"
    apple: "KivySchoolData.AppleData | None"
    bootstrap: str

    def __init__(self, data: dict):
        self.app_name = data.get("app_name")
        # self.ios = KivySchoolData.IosData(data["ios"]) if "ios" in data else None
        # self.macos = (
        #     KivySchoolData.MacosData(data["macos"]) if "macos" in data else None
        # )
        self.apple = self.AppleData(
            self.AppleData.IosData(data["ios"]) if "ios" in data else None,
            self.AppleData.MacosData(data["macos"]) if "macos" in data else None
        )
        self.android = (
            KivySchoolData.AndroidData(data["android"]) if "android" in data else None
        )
        self.bootstrap = data.get("bootstrap", "kivy")
    
    class AppleData:

        def __init__(self, ios: "IosData | None", macos: "MacosData | None"):
            self.ios = ios
            self.macos = macos

        class IosData:
            bundle_id: str
            info_plist: dict
            entitlements: dict
            permissions: list[str]
            frameworks: list[str]
            site_frameworks: list[str]
            developer_team: str | None
            minimum_deployment: str | None
            pre_build: Path | None
            post_build: Path | None

            def __init__(self, data: dict):
                self.bundle_id = data["bundle_id"]
                self.info_plist = data.get("info_plist", {})
                self.entitlements = data.get("entitlements", {})
                self.permissions = data.get("permissions", [])
                self.frameworks = data.get("frameworks", [])
                self.site_frameworks = data.get("site_frameworks", [])
                self.developer_team = data.get("developer_team")
                self.minimum_deployment = data.get("minimum_deployment")
                self.pre_build = Path(data.get("pre_build")) if "pre_build" in data else None # type: ignore
                self.post_build = Path(data.get("post_build")) if "post_build" in data else None # type: ignore

        class MacosData:
            bundle_id: str
            info_plist: dict
            entitlements: dict
            permissions: list[str]
            developer_team: str | None
            minimum_deployment: str | None
            archs: list[str]
            pre_build: Path | None
            post_build: Path | None

            def __init__(self, data: dict):
                self.bundle_id = data["bundle_id"]
                self.info_plist = data.get("info_plist", {})
                self.entitlements = data.get("entitlements", {})
                self.permissions = data.get("permissions", [])
                self.developer_team = data.get("developer_team")
                self.minimum_deployment = data.get("minimum_deployment")
                self.archs = data.get("archs", ["arm64", "x86_64"])
                self.pre_build = Path(data.get("pre_build")) if "pre_build" in data else None # type: ignore
                self.post_build = Path(data.get("post_build")) if "post_build" in data else None # type: ignore

    

    class AndroidData:
        package_name: str
        archs: list["Arch"]

        api: int | None
        min_api: int | None
        sdk: str | None
        ndk: str | None
        ndk_api: int | None

        sdk_path: Path | None
        ndk_path: Path | None
        java_path: Path | None
        global_tools: bool
        global_tools_path: Path | None
        icon: str | None
        presplash: str | None
        presplash_color: str | None
        presplash_lottie: str | None
        permissions: list[str]
        meta_data: dict[str, str]
        gradle_dependencies: list[str]
        gradle_plugins: list[str]
        services: list["ServiceData"]
        version_code: int
        version_name: str
        include_files: list[tuple[str, list[str]]]

        pre_build: Path | None
        post_build: Path | None

        byte_compile_python: bool

        def __init__(self, data: dict):
            self.package_name = data["package_name"]
            self.archs = [
                self.Arch(a) for a in data.get("archs", [])
            ]
            self.api = data.get("api")
            self.min_api = data.get("min_api")
            self.sdk = data.get("sdk")
            self.ndk = data.get("ndk")
            self.ndk_api = data.get("ndk_api")
            self.sdk_path = Path(data["sdk_path"]) if data.get("sdk_path") else None
            self.ndk_path = Path(data["ndk_path"]) if data.get("ndk_path") else None
            self.java_path = Path(data["java_path"]) if data.get("java_path") else None
            self.global_tools = bool(data.get("global_tools", False))
            self.global_tools_path = (
                Path(data["global_tools_path"])
                if data.get("global_tools_path")
                else None
            )
            self.icon = data.get("icon")
            self.presplash = data.get("presplash")
            self.presplash_color = (
                data.get("presplash_color")
                if data.get("presplash_color")
                else "#FFFFFF"
            )
            self.presplash_lottie = data.get("presplash_lottie")
            self.permissions = data.get("permissions", [])
            self.meta_data = data.get("meta_data", {})
            self.gradle_dependencies = data.get("gradle_dependencies", [])
            self.gradle_plugins = data.get("gradle_plugins", [])
            raw_includes = data.get("include_files", [])
            self.include_files = []
            for item in raw_includes:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    dest = str(item[0])
                    if len(item) == 2 and isinstance(item[1], (list, tuple)):
                        sources = [str(x) for x in item[1]]
                    else:
                        sources = [str(x) for x in item[1:]]
                    self.include_files.append((dest, sources))
            self.services = [
                self.ServiceData(s) for s in data.get("services", [])
            ]
            self.version_code = data.get("version_code", 1)
            self.version_name = data.get("version_name", "1.0")

            self.pre_build = Path(data.get("pre_build")) if "pre_build" in data else None # type: ignore
            self.post_build = Path(data.get("post_build")) if "post_build" in data else None # type: ignore

            self.byte_compile_python = bool(data.get("byte_compile_python", True))
            
        def kivyschool_root(self, working_dir: Path) -> Path:
            """Root for kivy-school managed tools/caches.

            ``global_tools = False`` (default) → ``<working_dir>/.kivyschool`` (project-local).
            ``global_tools = True``            → ``global_tools_path`` if set, else ``~/.kivyschool``.
            """
            if not self.global_tools:
                return working_dir / ".kivyschool"
            if self.global_tools_path is not None:
                return self.global_tools_path
            return Path.home() / ".kivyschool"
        
        class Arch(StrEnum):
            ARM64_V8A = "arm64-v8a"
            X86_64 = "x86_64"
        
        class ServiceData:
            name: str
            entrypoint: str
            foreground: bool
            foreground_service_type: str | None
            start_type: str
            notification_title: str
            notification_text: str
            notification_icon: str

            def __init__(self, data: dict):
                self.name = data["name"]
                # Enforce module syntax if they accidentally leave ".py" or "/"

                raw_entry = data.get("entrypoint", "service_main")
                self.entrypoint = raw_entry.replace("/", ".").replace(".py", "")
                self.foreground = data.get("foreground", False)
                self.foreground_service_type = data.get("foreground_service_type")
                self.start_type = data.get("start_type", "START_NOT_STICKY")
                self.notification_title = data.get(
                    "notification_title", f"{self.name} is running"
                )
                self.notification_text = data.get(
                    "notification_text", "Background task active"
                )
                self.notification_icon = data.get("notification_icon", "stat_notify_sync")



class ToolData:

    kivy_school: KivySchoolData | None

    def __init__(self, data: dict):
        self.kivy_school = (
            KivySchoolData(data["kivy-school"]) if "kivy-school" in data else None
        )


class Project:
    name: str

    def __init__(self, data: dict):
        self.name = data["name"]


class PyProjectToml:

    project: Project
    tool: ToolData

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = self._load_toml()
        self.project = Project(self.data["project"])
        self.tool = ToolData(self.data.get("tool", {}))

    def _load_toml(self) -> dict:
        with open(self.file_path, "r") as f:
            return toml.load(f)

    def save(self):
        with open(self.file_path, "w") as f:
            toml.dump(self.data, f)
