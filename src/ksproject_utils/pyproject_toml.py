from enum import Enum
from pathlib import Path

import toml


class KivySchoolData:

    app_name: str | None
    ios: "KivySchoolData.IosData | None"
    macos: "KivySchoolData.MacosData | None"
    android: "KivySchoolData.AndroidData | None"

    def __init__(self, data: dict):
        self.app_name = data.get("app_name")
        self.ios = KivySchoolData.IosData(data["ios"]) if "ios" in data else None
        self.macos = (
            KivySchoolData.MacosData(data["macos"]) if "macos" in data else None
        )
        self.android = (
            KivySchoolData.AndroidData(data["android"]) if "android" in data else None
        )

    class IosData:
        bundle_id: str
        info_plist: dict
        entitlements: dict
        permissions: list[str]
        frameworks: list[str]
        site_frameworks: list[str]
        developer_team: str | None

        def __init__(self, data: dict):
            self.bundle_id = data["bundle_id"]
            self.info_plist = data.get("info_plist", {})
            self.entitlements = data.get("entitlements", {})
            self.permissions = data.get("permissions", [])
            self.frameworks = data.get("frameworks", [])
            self.site_frameworks = data.get("site_frameworks", [])
            self.developer_team = data.get("developer_team")

    class MacosData:
        bundle_id: str
        info_plist: dict
        entitlements: dict
        developer_team: str | None

        def __init__(self, data: dict):
            self.bundle_id = data["bundle_id"]
            self.info_plist = data.get("info_plist", {})
            self.entitlements = data.get("entitlements", {})
            self.developer_team = data.get("developer_team")

    class ServiceData:
        name: str
        entrypoint: str
        foreground: bool
        foreground_service_type: str | None

        def __init__(self, data: dict):
            self.name = data["name"]
            # Enforce module syntax if they accidentally leave ".py" or "/"
            raw_entry = data.get("entrypoint", "service_main")
            self.entrypoint = raw_entry.replace("/", ".").replace(".py", "")

            self.foreground = data.get("foreground", False)
            self.foreground_service_type = data.get("foreground_service_type")

    class AndroidData:
        package_name: str
        archs: list["KivySchoolData.AndroidData.Arch"]

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
        services: list["KivySchoolData.ServiceData"]

        def __init__(self, data: dict):
            self.package_name = data["package_name"]
            self.archs = [
                KivySchoolData.AndroidData.Arch(a) for a in data.get("archs", [])
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
            self.global_tools_path = Path(data["global_tools_path"]) if data.get("global_tools_path") else None
            self.icon = data.get("icon")
            self.presplash = data.get("presplash")
            self.presplash_color = data.get("presplash_color") if data.get("presplash_color") else "#FFFFFF"
            self.presplash_lottie = data.get("presplash_lottie")
            self.permissions = data.get("permissions", [])
            self.meta_data = data.get("meta_data", {})
            self.gradle_dependencies = data.get("gradle_dependencies", [])

            # Parse the list of services
            self.services = [
                KivySchoolData.ServiceData(s) for s in data.get("services", [])
            ]

        def kivyschool_root(self, working_dir: Path) -> Path:
            """Root for kivy-school managed tools/caches.

            ``global_tools = False`` (default) → ``<working_dir>/.kivyschool`` (project-local).
            ``global_tools = True``             → ``global_tools_path`` if set, else ``~/.kivyschool``.
            """
            if not self.global_tools:
                return working_dir / ".kivyschool"
            if self.global_tools_path is not None:
                return self.global_tools_path
            return Path.home() / ".kivyschool"

        class Arch(Enum):
            ARM64_V8A = "arm64-v8a"
            X86_64 = "x86_64"


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
