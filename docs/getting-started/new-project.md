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
3. **`ksproject init`** appends `[tool.kivy-school]` configuration with sensible defaults for Android, iOS, and macOS
4. **Writes starter app sources** — a working Kivy app with a `.kv` layout file
5. **Creates a `wheelhouse/`** directory for caching platform wheels
6. **Generates `AndroidManifest.tmpl.xml`** — the template for Android manifest generation

### Options

| Flag | Description |
|------|-------------|
| `--name NAME` | Set the app/module name (defaults to the directory name) |

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
├── AndroidManifest.tmpl.xml      # Android manifest template
├── wheelhouse/                   # Wheel cache (empty)
└── src/
    └── myapp/
        ├── __init__.py
        ├── __main__.py           # Entry point
        ├── app.py                # Kivy application code
        └── app.kv                # KV language UI layout
```

### The Starter App

The generated `app.py` contains a working Kivy application:

```python
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
import os

class IntroScreen(BoxLayout):
    def on_button_click(self):
        self.ids.subtitle_label.text = "Explore the power of Python + KVLang!"

class KivyIntroApp(App):
    def build(self):
        Builder.load_file(os.path.join(self.directory, "app.kv"))
        return IntroScreen()

def main():
    app = KivyIntroApp()
    app.run()
```

The `app.kv` file provides a styled dark-theme welcome screen with a feature card and button — ready to customize.

---

## The Generated pyproject.toml

After initialization, your `pyproject.toml` will contain standard Python project metadata plus a `[tool.kivy-school]` section:

```toml
[project]
name = "myapp"
version = "0.1.0"
description = ""
requires-python = ">=3.13"
dependencies = [
    "kivy>=2.3.1,<3.0.0",
]

[project.scripts]
myapp = "myapp:main"

[tool.uv]
extra-index-url = [
    "https://pypi.anaconda.org/pyswift/simple",
    "https://pypi.anaconda.org/kivyschool/simple",
]

[tool.kivy-school]
app_name = "myapp"

[tool.kivy-school.android]
package_name = "org.kivyschool.myapp"
archs = ["arm64-v8a"]
permissions = ["INTERNET"]

[tool.kivy-school.ios]
bundle_id = "org.kivyschool.myapp"

[tool.kivy-school.macos]
bundle_id = "org.kivyschool.myapp"
```

!!! tip "Extra Index URLs"
    The `extra-index-url` entries point to the **PySwift** and **KivySchool** Anaconda channels. These host pre-compiled cross-platform wheels (Kivy for Android/iOS, CPython builds, SDL2 frameworks) that ksproject downloads during mobile builds.

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

---

## Initializing Into an Existing Directory

You can also run `ksproject init` in an existing Python project that already has ksproject as a dev dependency:

```bash
cd existing-project
uv add git+https://github.com/kivy-school/ksproject --dev
uv run ksproject init .
```

If a `pyproject.toml` already exists, ksproject will:

- **Skip** `uv init` (won't overwrite your existing config)
- **Append** the `[tool.kivy-school]` block if not already present
- **Write** the starter app sources (only if source files don't exist)
- **Create** the wheelhouse and manifest template

!!! warning
    If `[tool.kivy-school]` already exists in your pyproject.toml, the init command will detect it and skip the configuration step.
