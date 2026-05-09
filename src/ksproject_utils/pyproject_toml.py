import toml



class KivySchoolData:

    ios: "IosData" | None
    android: "AndroidData" | None
    
    class IosData:
        app_name: str
        bundle_id: str

        def __init__(self, data: dict):
            self.bundle_id = data["bundle_id"]

    class AndroidData:
        app_name: str
        package_name: str

        def __init__(self, data: dict):
            self.app_name = data["app_name"]
            self.package_name = data["package_name"]

class ToolData:

    kivy_school: KivySchoolData | None

    def __init__(self, data: dict):
        self.kivy_school = KivySchoolData(data["kivy_school"]) if "kivy_school" in data else None



class PyProjectToml:

    project: ToolData
    tool: ToolData

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = self._load_toml()

    def save(self):
        with open(self.file_path, 'w') as f:
            toml.dump(self.data, f)

    class Project:
        name: str

