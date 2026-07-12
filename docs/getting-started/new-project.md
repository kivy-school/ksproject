# New Project

This guide walks you through creating a new ksproject from scratch. Since installing ksproject and creating a project are a single step, there's no separate "installation" page — everything happens together.

---

## Prerequisites

You need **Python 3.13+** and **[uv](https://docs.astral.sh/uv/)** installed on your system.

=== "macOS"

    ```bash
    # Install uv (Python package manager)
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Linux"

    ```bash
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    # Install uv
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

---

## Create a New Project

```bash
uv init --package myapp --python 3.13
cd myapp
uv add git+https://github.com/kivy-school/ksproject --dev
uv run ksproject init
```

This does everything:

1. **Creates a proper Python project** with `pyproject.toml` via `uv init`
2. **Adds ksproject as a dev dependency** — local to this project, not installed globally
3. **`ksproject init`** appends `[tool.kivy-school]` configuration with commented defaults for Android, iOS, and macOS
4. **Writes starter app sources** — a working Kivy app with a `.kv` layout file
5. **Creates a `wheelhouse/`** directory (with a `.gitkeep`) for [local platform wheels](../wheelhouse/overview.md)
6. **Generates build templates** — `AndroidManifest.tmpl.xml` and `build.tmpl.gradle.kts`, which you can edit to customize the generated Android project
7. **Writes a `.gitignore` and a `.env`** — the `.env` holds placeholders for Android signing credentials (`KEYSTORE`, `STOREPASS`, `KEYALIAS`, `KEYPASS`)

### Options

| Flag | Description |
|------|-------------|
| `path` | Project directory (default: current directory) |
| `--name NAME` | Set the app name (defaults to the directory name) |

### Example

```bash
uv init --package my-kivy-app --python 3.13
cd my-kivy-app
uv add git+https://github.com/kivy-school/ksproject --dev
uv run ksproject init --name mykivyapp
```

---

## What Gets Created

After running `uv run ksproject init`, you'll have this structure:

```
myapp/
├── pyproject.toml                # Project config + [tool.kivy-school]
├── AndroidManifest.tmpl.xml      # Android manifest template (editable)
├── build.tmpl.gradle.kts         # App-module Gradle template (editable)
├── .env                          # Signing credential placeholders (gitignored)
├── .gitignore
├── .java/                        # Project-level Java sources for Android
├── wheelhouse/                   # Local wheel repository
│   └── .gitkeep
└── src/
    └── myapp/
        ├── __init__.py
        ├── __main__.py           # Entry point
        ├── app.py                # Kivy application code
        ├── app.kv                # KV language UI layout
        └── services/             # Android background service entrypoints
            └── __init__.py
```

### The Starter App

The generated `app.py` contains a working Kivy application:

```python
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.lang import Builder

class IntroScreen(BoxLayout):
    def on_button_click(self):
        self.ids.subtitle_label.text = "Explore the power of Python + KVLang!"
        self.ids.action_btn.text = "Ready to Build!"

class KivyIntroApp(App):
    def build(self):
        Window.clearcolor = [1, 1, 1, 1]
        Builder.load_file(os.path.join(self.directory, "app.kv"))
        return IntroScreen()

def main():
    app = KivyIntroApp()
    app.run()
```

The `app.kv` file provides a styled welcome screen with a feature card and button — ready to customize.

---

## The Generated pyproject.toml

After initialization, your `pyproject.toml` contains standard Python project metadata plus the ksproject configuration. The generated file is heavily commented — the essential parts look like this:

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "kivy>=2.3.1,<3.0.0",
]

[project.scripts]
myapp = "myapp:main"

[tool.uv]
index-strategy = "unsafe-best-match"
find-links = ["./wheelhouse"]

[tool.uv.pip]
extra-index-url = [
    "https://pypi-index.psychowaspx.workers.dev/simple",
    "https://pypi.anaconda.org/kivyschool/simple",
]
find-links = ["./wheelhouse"]

[tool.kivy-school]
app_name = "myapp"
bootstrap = "kivy"

[tool.kivy-school.android]
package_name = "org.example.myapp"
version_code = 1
archs = ["arm64-v8a"]
api = 36
min_api = 24
sdk = "36"
ndk = "28c"
ndk_api = 24
global_tools = true
byte_compile_python = true

[tool.kivy-school.ios]
bundle_id = "org.example.myapp"

[tool.kivy-school.macos]
bundle_id = "org.example.myapp"
```

!!! tip "Extra Index URLs & Wheelhouse"
    The `extra-index-url` entries point to the **KivySchool** wheel indexes, which host pre-compiled cross-platform wheels (Kivy for Android/iOS/macOS, CPython builds) that ksproject downloads during mobile builds. The `find-links = ["./wheelhouse"]` entries make your local [wheelhouse](../wheelhouse/overview.md) an additional wheel source, and `index-strategy = "unsafe-best-match"` lets uv pick the best wheel across all of these sources.

See the **[pyproject.toml Reference](../configuration/pyproject-toml.md)** for every available key.

---

## Pinning the Python Version

ksproject reads your project's `.python-version` file to decide which CPython to bundle. A bare `3.13` (or no file) uses ksproject's built-in default. You can also pin an exact patch release — it must be one that BeeWare's Python-Apple-support ships (currently `3.13.8`, `3.13.11`, `3.13.14`, `3.14.2`, `3.14.6`):

```bash
echo "3.13.11" > .python-version
```

That version then drives everything: the bundled CPython on Android, the Python.xcframework on iOS/macOS, and the interpreter used to byte-compile your app.

---

## Running on Desktop

You can immediately run your app on desktop:

```bash
uv run myapp
```

This launches the Kivy app on your development machine — useful for rapid iteration before building for mobile.

---

## Next Steps

Your project is ready to build for mobile platforms:

- **[Build for Android](../android/building.md)** — Build an APK and run on emulator or device
- **[Build for iOS](../ios/building.md)** — Build an .app and run on simulator or device
- **[Configure your app](../configuration/pyproject-toml.md)** — Customize package name, permissions, services, and more
- **[Add plugins](../plugins/overview.md)** — Install pip packages that add Java code, Gradle dependencies, or iOS frameworks
- **[Use the wheelhouse](../wheelhouse/overview.md)** — Feed your own platform wheels into mobile builds

---

## Initializing Into an Existing Directory

You can also run `ksproject init` in an existing Python project that already has ksproject as a dev dependency:

```bash
cd existing-project
uv add git+https://github.com/kivy-school/ksproject --dev
uv run ksproject init
```

If a `pyproject.toml` already exists, ksproject will:

- **Skip** `uv init` (won't overwrite your existing config)
- **Append** the `[tool.kivy-school]` block if not already present
- **Keep** existing `AndroidManifest.tmpl.xml` / `build.tmpl.gradle.kts` files untouched
- **Create** the wheelhouse if missing

!!! warning "Starter sources are overwritten"
    `ksproject init` always writes the starter `app.py`, `app.kv`, `__init__.py`, and `__main__.py` into `src/<module>/` — re-running it in a project where you've already customized those files will overwrite them. It also rewrites `.gitignore` and `.env`. The `[tool.kivy-school]` config, manifest, and Gradle templates are safe: they're only written when missing.
