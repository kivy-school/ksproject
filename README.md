# ksproject

Kivy School Project Manager — cross-platform build tool for Kivy apps targeting
Android (and iOS, soon). Generates a pure AGP Gradle project, downloads the
Android SDK / NDK / JDK on demand, and builds an APK or AAR.

No `buildozer`, no `python-for-android` at build time — just a clean Gradle
project under `project_dist/gradle/` that you can also open in Android Studio.

---

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/) (used for env + dependency management)

Everything else (Android SDK, NDK, JDK, Gradle wrapper) is downloaded
automatically on first build into `.kivyschool/` inside your project.

---

## 1. Create a new project

```bash
uv init --package hello-world --python 3.13
cd hello-world
uv add git+https://github.com/kivy-school/ksproject --dev
uv run ksproject init
```

`ksproject init` writes a starter `main.py`, scaffolds `src/hello_world/`, and
adds a `[tool.kivy-school]` block to your `pyproject.toml`.

## 2. Add Kivy

```bash
uv add kivy
```

## 3. Add platform-specific deps

`pyjnius` is only meaningful on Android. Mark it with a PEP 508 marker so `uv`
won't try to install it on macOS / Linux / Windows:

```bash
uv add "pyjnius ; sys_platform == 'android'"
```

Same trick for iOS (later):

```bash
uv add "pyobjus ; sys_platform == 'ios'"
```

Optional scientific stack:

```bash
uv add numpy matplotlib
```

## 4. Run on desktop

```bash
uv run hello-world
```

This launches the entry point declared in `pyproject.toml` — same code that
will run on Android, no changes needed.

---

## 5. Build for Android

```bash
uv run ksproject android build
```

First run downloads:

- Android command-line tools + SDK (platform `android-35`, build-tools, etc.)
- NDK `27.3.13750724`
- Temurin JDK 21 (via `sdkman`)
- Gradle 9.5.0 wrapper
- CPython-for-Android prebuilt wheels

into `~/.android-sdk` and `<project>/.kivyschool/`. Subsequent builds are
incremental.

The output APK lands at:

```
project_dist/gradle/app/build/outputs/apk/debug/app-debug.apk
```

### Release builds

```bash
uv run ksproject android build release
```

### AAR (library) instead of APK

```bash
uv run ksproject android build --aar
uv run ksproject android build release --aar
```

Output:

```
project_dist/gradle/app/build/outputs/aar/app-{debug,release}.aar
```

---

## 6. Install and run on an emulator

List attached devices and available AVDs:

```bash
uv run ksproject android devices
```

Example output:

```
avd     name=Pixel9
device  serial=emulator-5554     state=device       model=sdk_gphone64_arm64
```

Boot an AVD by name (boots it, then builds + installs + launches):

```bash
uv run ksproject android run --name Pixel9
```

## 7. Run on a real device

Plug a phone in over USB with **USB debugging** enabled (Settings → Developer
options → USB debugging). Authorise the host when the dialog pops up.

Find its adb serial:

```bash
uv run ksproject android devices
# device  serial=R3CN30XXXXX  state=device  model=SM-G998B
```

Run by serial:

```bash
uv run ksproject android run --uuid R3CN30XXXXX
```

`--variant release` works the same way:

```bash
uv run ksproject android run --uuid R3CN30XXXXX --variant release
```

---

## 8. Configuring `[tool.kivy-school.android]`

All of these are optional except `package_name`:

```toml
[tool.kivy-school]
app_name = "Hello World"

[tool.kivy-school.android]
package_name = "org.example.hello_world"
archs = ["arm64-v8a", "x86_64"]
api = 35
min_api = 24
ndk = "27.3.13750724"
ndk_api = 24

# Assets — paths relative to the project root
# icon = "assets/icon.png"
# presplash = "assets/presplash.jpg"

# Android manifest permissions (default: just INTERNET)
# permissions = ["INTERNET", "ACCESS_NETWORK_STATE"]

# Maven dependencies added to app/build.gradle.kts
# gradle_dependencies = [
#     "com.google.android.gms:play-services-ads:22.6.0",
# ]

# <meta-data> entries inside <application> in AndroidManifest.xml
# [tool.kivy-school.android.meta_data]
# "com.google.android.gms.ads.APPLICATION_ID" = "ca-app-pub-xxxxxxxx~xxxxxxxx"

# Pin toolchain paths (skip the auto-download)
# sdk_path  = "/path/to/android-sdk"
# ndk_path  = "/path/to/android-sdk/ndk/27.3.13750724"
# java_path = "/path/to/jdk"

# Declare services as (assuming you have all your services in `services` folder in root dir containing pyproject.toml)
#services = [
#    { name = "MyService1", entrypoint = "services.myservice1", foreground = true, foreground_service_type = "location|dataSync" },
#    { name = "MyService2", entrypoint = "services.myservice2", foreground = true, foreground_service_type = "location|dataSync" },
#    { name = "MyService3", entrypoint = "services.myservice3", foreground = true, foreground_service_type = "dataSync" },
#]

# OR


# [[tool.kivy-school.android.services]]
# name = "MyService1"
# entrypoint = "services.myservice1"
# foreground = true
# foreground_service_type = "location|dataSync"
# 
# [[tool.kivy-school.android.services]]
# name = "MyService2"
# entrypoint = "services.myservice2"
# foreground = true
# foreground_service_type = "location|dataSync"
# 
# [[tool.kivy-school.android.services]]
# name = "MyService3"
# entrypoint = "services.myservice3"
# foreground = true
# foreground_service_type = "dataSync"

```

---

## Command reference

| Command                                          | What it does                               |
| ------------------------------------------------ | ------------------------------------------ |
| `ksproject init`                                 | Scaffold a new project in the current dir  |
| `ksproject android build [debug\|release]`       | Build an APK                               |
| `ksproject android build --aar [debug\|release]` | Build an AAR library                       |
| `ksproject android devices`                      | List adb devices and AVDs                  |
| `ksproject android run --name <AVD>`             | Build, install, and launch on an emulator  |
| `ksproject android run --uuid <serial>`          | Build, install, and launch on a USB device |

Add `--variant release` to `run` for a release build.
