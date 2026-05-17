from enum import Enum
from pathlib import Path

import toml


class KivySchoolData:

    app_name: str | None
    ios: "KivySchoolData.IosData | None"
    android: "KivySchoolData.AndroidData | None"

    def __init__(self, data: dict):
        self.app_name = data.get("app_name")
        self.ios = KivySchoolData.IosData(data["ios"]) if "ios" in data else None
        self.android = (
            KivySchoolData.AndroidData(data["android"]) if "android" in data else None
        )

    class IosData:
        bundle_id: str

        def __init__(self, data: dict):
            self.bundle_id = data["bundle_id"]

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
        icon: str | None
        presplash: str | None
        permissions: list[str]
        meta_data: dict[str, str]
        gradle_dependencies: list[str]

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
            self.icon = data.get("icon")
            self.presplash = data.get("presplash")
            self.permissions = data.get("permissions", [])
            self.meta_data = data.get("meta_data", {})
            self.gradle_dependencies = data.get("gradle_dependencies", [])

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
