def _main_keys(app_name: str, indexes: list[str]) -> str:
    extra_index = ",\n".join(f'    "{u}"' for u in indexes)

    return f"""\
[tool.uv]
index-strategy = "unsafe-best-match"
find-links = ["./wheelhouse"]

[tool.uv.pip]
extra-index-url = [
{extra_index}
]
find-links = ["./wheelhouse"]

#### kivy-school configuration ####

[tool.kivy-school]
app_name = "{app_name}"
"""


def _android_keys(module_name: str) -> str:
    return f"""\
[tool.kivy-school.android]
package_name = "org.example.{module_name}"
archs = [
    "arm64-v8a", 
    # "x86_64" # Uncomment if you want to support x86_64 (emulators), but it will increase APK size
]
gradle_dependencies = [
    # "com.onesignal:OneSignal:[5.6.1, 5.9.99]" # Example of adding OneSignal for push notifications; adjust version as needed
]
permissions = [
    # "POST_NOTIFICATIONS", "INTERNET", "ACCESS_NETWORK_STATE", "WAKE_LOCK" # Example permissions; add as needed
]

api = 36
min_api = 24
sdk = "36"
ndk = "28c"
ndk_api = 24

local_tools = True # Set to True to use local SDK/NDK (./.kivyschool); set to False to use user-installed versions ~/.kivyschool

# sdk_path = "/path/to/android-sdk"
# ndk_path = "/path/to/android-ndk"
# java_path = "/path/to/jdk"
"""


def _ios_keys(module_name: str) -> str:
    return f"""\
[tool.kivy-school.ios]
bundle_id = "org.example.{module_name}"
info_plist = {{}}
entitlements = {{}}
permissions = []
frameworks = []
"""


def _macos_keys(module_name: str) -> str:
    return f"""\
[tool.kivy-school.macos]
bundle_id = "org.example.{module_name}"
info_plist = {{}}
entitlements = {{}}
"""


class PyProjectInitKeys:

    module_name: str
    app_name: str

    EXTRA_INDEX_URLS = [
        # "https://pypi.anaconda.org/beeware/simple",
        "https://pypi.anaconda.org/pyswift/simple",
        "https://pypi.anaconda.org/kivyschool/simple",
    ]

    def __init__(self, project_name: str):
        self.module_name = project_name.lower().replace("-", "_").replace(".", "_")
        self.app_name = project_name

    def main_keys(self) -> str:
        return _main_keys(self.app_name, self.EXTRA_INDEX_URLS)

    def android_keys(self) -> str:
        return _android_keys(self.module_name)

    def ios_keys(self) -> str:
        return _ios_keys(self.module_name)

    def macos_keys(self) -> str:
        return _macos_keys(self.module_name)

    def output(self) -> str:
        return f"""\
{self.main_keys()}
{self.android_keys()}
{self.ios_keys()}
{self.macos_keys()}
"""
