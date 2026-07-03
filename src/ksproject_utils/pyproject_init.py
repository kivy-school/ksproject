from .gradle.android_toolchain import DEFAULT_API_VERSION, DEFAULT_SDK_VERSION


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
bootstrap = "kivy"
"""


def _android_keys(module_name: str) -> str:
    return f"""\
[tool.kivy-school.android]
package_name = "org.example.{module_name}"

# version_name = "0.1" # change when you want to release a very new version
version_code = 1 # keep increasing to make an update to existing version_name (bug fixes/security releases)

# icon = "relative to pyproject (png)"
# presplash_color = "#FFFFFF"
# presplash = "relative to pyproject (png,jpg,gif)"
# presplash_lottie = "relative to pyproject (json)"

archs = [
    "arm64-v8a", 
    # "x86_64" # Uncomment if you want to support x86_64 (emulators), but it will increase APK size
]
gradle_dependencies = [
    # "com.onesignal:OneSignal:[5.6.1, 5.9.99]" # Example of adding OneSignal for push notifications; adjust version as needed
]
gradle_plugins = [
    # 'id("com.google.gms.google-services") version "4.4.2" apply false'
]
permissions = [
    # "POST_NOTIFICATIONS", "INTERNET", "ACCESS_NETWORK_STATE", "WAKE_LOCK" # Example permissions; add as needed
]

api = {DEFAULT_API_VERSION}
min_api = 24
sdk = "{DEFAULT_SDK_VERSION}"
ndk = "28c"
ndk_api = 24

global_tools = true # Set to <false> to use project-local SDK/NDK (./.kivyschool); set to <true> to use shared/global versions (~/.kivyschool or global_tools_path)
#global_tools_path = "~/.kivyschool" # Override root path when global_tools = true; ignored when global_tools = false

# sdk_path = "/path/to/android-sdk"
# ndk_path = "/path/to/android-ndk"
# java_path = "/path/to/jdk"

# # Format 1: Flat list (Destination, Source 1, Source 2)
# include_files = [
#     ["gradle/app", "./google-services.json", "./some-other-config.xml"]
# ]

# # Format 2: Nested list (Destination, [Source 1, Source 2])
# include_files = [
#     ["gradle/app", ["./google-services.json", "./some-other-config.xml"]]
# ]

# pre_build = "path/to/android_prebuild.py"
# post_build = "path/to/android_prebuild.py"

byte_compile_python = true

# <meta-data> entries inside <application>
# [tool.kivy-school.android.meta_data]
# "com.google.android.gms.ads.APPLICATION_ID" = "ca-app-pub-xxxxxxxx~xxxxxxxx"

# --- Services ---
# [[tool.kivy-school.android.services]]
# name = "MyService1"
# start_type = "START_NOT_STICKY"
# entrypoint = "hello_world.services.myservice1"
# foreground = true
# foreground_service_type = "location|dataSync"
# notification_title = "MyService1 Running"
# notification_text = "Service is managing background data."
# notification_icon = "stat_notify_sync"
"""


def _ios_keys(module_name: str) -> str:
    return f"""\
[tool.kivy-school.ios]
bundle_id = "org.example.{module_name}"
minimum_deployment = "15.6"
info_plist = {{}}
entitlements = {{}}
permissions = []
frameworks = []
#developer_team = "ABC123XYZ" # Set to your Apple Developer Team ID (e.g. ABC123XYZ) to enable automatic code signing; leave as null for manual signing
# pre_build = "path/to/ios_prebuild.py"
# post_build = "path/to/ios_postbuild.py"
"""


def _macos_keys(module_name: str) -> str:
    return f"""\
[tool.kivy-school.macos]
bundle_id = "org.example.{module_name}"
minimum_deployment = "11.5"
info_plist = {{}}
entitlements = {{}}
#developer_team = "ABC123XYZ" # Set to your Apple Developer Team ID (e.g. ABC123XYZ) to enable automatic code signing; leave as null for manual signing
# pre_build = "path/to/android_prebuild.py"
# post_build = "path/to/android_postbuild.py"
"""


class PyProjectInitKeys:

    module_name: str
    app_name: str

    EXTRA_INDEX_URLS = [
        "https://pypi-index.psychowaspx.workers.dev/simple",
        "https://pypi.anaconda.org/kivyschool/simple",
        # "https://pypi.anaconda.org/pyswift/simple",
        # "https://pypi.anaconda.org/beeware/simple",
    ]

    def __init__(self, project_name: str):
        self.module_name = project_name.lower().replace("-", "_").replace(".", "_").replace(" ", "")
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
