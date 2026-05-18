"""Initialize a new ksproject (or upgrade an existing uv project).

Ports `PSProject/Sources/PSProject/Init.swift` + `NewToml.swift`.
Drops Swift/iOS/macOS-specific keys; keeps android section.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import toml

from .tools import get_uv


class ProjectInitError(Exception):
    pass


class ProjectInit:

    EXTRA_INDEX_URLS = [
        "https://pypi.anaconda.org/beeware/simple",
        "https://pypi.anaconda.org/pyswift/simple",
        "https://pypi.anaconda.org/kivyschool/simple",
    ]

    def __init__(self, project_path: Path, app_name: str | None = None):
        self.project_path = Path(project_path).resolve()
        self.app_name = app_name or self.project_path.name
        self.module_name = self._resolve_module_name(self.app_name)
        self.pyproject_path = self.project_path / "pyproject.toml"

    @staticmethod
    def _resolve_module_name(name: str) -> str:
        return name.replace("-", "_").replace(".", "_")

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.project_path.mkdir(parents=True, exist_ok=True)

        if not self.pyproject_path.exists():
            self._uv_init()

        if self._already_kivyschool():
            print(f"[ksproject] {self.pyproject_path} already has [tool.kivy-school]; skipping toml updates")
        else:
            self._append_kivyschool_config()

        self._write_app_sources()
        self._ensure_wheelhouse()
        self._ensure_base_dirs()
        print(f"[ksproject] initialized at {self.project_path}")

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _uv_init(self) -> None:
        uv = get_uv()
        if uv is None:
            raise ProjectInitError(
                "`uv` not found in PATH; install uv to initialize a new project"
            )
        result = subprocess.run(
            [uv, "init", "--name", self.app_name, str(self.project_path)],
        )
        if result.returncode != 0:
            raise ProjectInitError(f"`uv init` exited with code {result.returncode}")

    def _already_kivyschool(self) -> bool:
        with self.pyproject_path.open("r") as f:
            data = toml.load(f)
        tool = data.get("tool", {})
        return "kivy-school" in tool

    def _append_kivyschool_config(self) -> None:
        existing = self.pyproject_path.read_text()
        if not existing.endswith("\n"):
            existing += "\n"

        block = self._kivyschool_block()
        self.pyproject_path.write_text(f"{existing}\n{block}")

    def _kivyschool_block(self) -> str:
        extra_index = ",\n".join(f'    "{u}"' for u in self.EXTRA_INDEX_URLS)
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
app_name = "{self.app_name}"

[tool.kivy-school.android]
archs = ["arm64-v8a"]
package_name = "org.example.{self.module_name}"
api = 36
min_api = 24
sdk = "36"
ndk = "27.3.13750724" # check source.properties inside ndk-dir
ndk_api = 24
# sdk_path = "/path/to/android-sdk"
# ndk_path = "/path/to/android-sdk/ndk/27.3.13750724"
# java_path = "/path/to/jdk"
"""

    def _write_app_sources(self) -> None:
        app_src = self.project_path / "src" / self.module_name
        app_src.mkdir(parents=True, exist_ok=True)

        # --- Define File Contents ---
        
        app_py_content = """import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.lang import Builder

class IntroScreen(BoxLayout):
    def on_button_click(self):
        # Update the subtitle text when the button is pressed
        self.ids.subtitle_label.text = "Explore the power of Python + KVLang!"
        self.ids.action_btn.text = "Ready to Build!"

class KivyIntroApp(App):
    def build(self):
        Window.clearcolor = [1, 1, 1, 1]
        # Using self.directory safely grabs the location where app.py lives
        Builder.load_file(os.path.join(self.directory, "app.kv"))
        return IntroScreen()

if __name__ == "__main__":
    KivyIntroApp().run()

"""

        app_kv_content = """<IntroScreen>:
    orientation: 'vertical'
    padding: dp(24)
    spacing: dp(20)
    
    # Background Canvas
    canvas.before:
        Color:
            rgba: (0.10, 0.11, 0.13, 1) # Dark Slate Gray
        Rectangle:
            pos: self.pos
            size: self.size

    # Header / Welcome Section
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.3
        spacing: dp(8)
        
        Label:
            text: "Welcome to Kivy"
            font_size: '28sp'
            bold: True
            color: (1, 1, 1, 1)
            halign: 'center'
            valign: 'middle'
            
        Label:
            id: subtitle_label
            text: "Your journey into cross-platform UI begins here."
            font_size: '14sp'
            color: (0.7, 0.7, 0.7, 1)
            halign: 'center'
            text_size: self.width, None

    # Feature Card (Visual Centerpiece)
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.4
        padding: dp(16)
        spacing: dp(12)
        canvas.before:
            Color:
                rgba: (0.16, 0.18, 0.21, 1) # Lighter card background
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]

        Label:
            text: "Why Kivy?"
            font_size: '18sp'
            bold: True
            color: (0.29, 0.69, 0.31, 1) # Fresh Green Accent
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'left'
            text_size: self.width, None

        Label:
            text: "• Fast & GPU Accelerated\\n• Same code for Android, iOS, Windows, & Mac\\n• Declarative UI with KVLang\\n• Open Source & Flexible"
            font_size: '14sp'
            color: (0.85, 0.85, 0.85, 1)
            line_height: 1.3
            valign: 'top'
            text_size: self.width, self.height

    # Action Section (Button)
    BoxLayout:
        size_hint_y: 0.3
        gravity: 'center'
        padding: [0, dp(40), 0, 0]
        
        Button:
            id: action_btn
            text: "Get Started"
            font_size: '16sp'
            bold: True
            size_hint: (1, None)
            height: dp(50)
            background_color: (0, 0, 0, 0) # Remove default background to style with canvas
            color: (1, 1, 1, 1)
            on_press: root.on_button_click()
            
            canvas.before:
                Color:
                    rgba: (0.29, 0.69, 0.31, 1) if self.state == 'normal' else (0.22, 0.53, 0.24, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [25] # Perfect pill-shaped button
"""

        init_py_content = f"""print("App initialized!!")
def main():
    from .app import KivyIntroApp
    app = KivyIntroApp()
    app.run()
"""

        main_py_content = """from . import main

if __name__ == "__main__":
    main()
"""

        # --- File Assignment Map ---
        files = {
            "app.py": app_py_content,
            "app.kv": app_kv_content,
            "__init__.py": init_py_content,
            "__main__.py": main_py_content,
        }

        # --- Target Write Loop ---
        for name, content in files.items():
            target = app_src / name
            if not self._already_kivyschool():
                target.write_text(content, encoding="utf-8")

        tmpl_path = (self.project_path / "AndroidManifest.tmpl.xml")
        if (not self._already_kivyschool()) or (not tmpl_path.exists()):
            default_manifest_template = """\
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

{{ permissions }}

    <application
        android:label="{{ app_name }}"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="true"
        android:supportsRtl="true"
        android:hardwareAccelerated="true"
        android:theme="@android:style/Theme.DeviceDefault.NoActionBar">{{ meta_data }}
{{ services }}
        <activity
            android:name=".MainActivity"
            android:label="{{ app_name }}"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:theme="@android:style/Theme.DeviceDefault.NoActionBar"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""
            tmpl_path.write_text(default_manifest_template, encoding="utf-8")

    def _ensure_wheelhouse(self) -> None:
        (self.project_path / "wheelhouse").mkdir(exist_ok=True)

    def _ensure_base_dirs(self) -> None:
        (self.project_path / ".java").mkdir(exist_ok=True)
        services_dir = self.project_path / "src" / self.module_name / "services"
        services_dir.mkdir(exist_ok=True)
        (services_dir / "__init__.py").touch()
