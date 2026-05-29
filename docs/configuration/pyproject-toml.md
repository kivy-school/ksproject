# pyproject.toml Reference

All ksproject configuration lives under `[tool.kivy-school]` in your `pyproject.toml`. This page documents every available key, its type, default value, and behavior.

---

## Root Configuration

```toml
[tool.kivy-school]
app_name = "My App"
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `app_name` | `string` | Project name from `[project]` | Display name of your application. Used as the app label on Android and the bundle display name on iOS/macOS. |

---

## Android Configuration

```toml
[tool.kivy-school.android]
package_name = "org.example.myapp"
archs = ["arm64-v8a"]
api = 36
min_api = 24
sdk = "36"
ndk = "28c"
ndk_api = 24
global_tools = false
permissions = ["INTERNET", "CAMERA"]
gradle_dependencies = [
    "com.google.firebase:firebase-analytics:21.0.0",
]
```

### Identity & Architecture

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `package_name` | `string` | **Required** | Java package name (e.g., `org.example.myapp`). Used as the Android application ID and Java package namespace. |
| `archs` | `list[string]` | `["arm64-v8a"]` | Target CPU architectures. Valid values: `arm64-v8a`, `x86_64`. Each arch gets its own site-packages with cross-compiled native extensions. |

### SDK & NDK Versions

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api` | `int` | `36` | **Compile SDK version** (also used as target SDK). Determines which Android API level your app compiles against. |
| `min_api` | `int` | `24` | **Minimum SDK version**. The lowest Android version your app supports (Android 7.0 = API 24). |
| `sdk` | `string` | `"36"` | SDK platform version string. Used in SDK paths like `platforms;android-{sdk}` and `system-images;android-{sdk};google_apis;{arch}`. |
| `ndk` | `string` | `"28c"` | NDK version shorthand. Mapped internally to full version strings (e.g., `28c` → `28.2.13676358`). |
| `ndk_api` | `int` | `24` | Native (C/C++) API level. The minimum Android version for native code. Usually matches `min_api`. |

!!! info "API vs SDK"
    `api` is an integer used for `compileSdk`/`targetSdk` in Gradle. `sdk` is a string used in SDK manager paths. They typically have the same numeric value but serve different purposes — never cast between them.

### Tool Paths

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `sdk_path` | `string` (path) | Auto-resolved | Override the Android SDK location. Skips automatic SDK download/installation. |
| `ndk_path` | `string` (path) | Auto-resolved | Override the NDK location. Skips automatic NDK download. |
| `java_path` | `string` (path) | Auto-resolved | Override the Java/JDK location. Must be Java 17–21 (Java 22+ crashes sdkmanager). |
| `global_tools` | `bool` | `false` | When `true`, installs SDK/NDK/Java to `~/.kivyschool/` (shared across projects). When `false`, uses `<project>/.kivyschool/` (project-local). |
| `global_tools_path` | `string` (path) | `~/.kivyschool` | Override the global tools directory when `global_tools = true`. |

### Tool Resolution Priority

ksproject resolves SDK/NDK/Java locations in this order:

1. **Environment variables** — `ANDROID_HOME` / `ANDROID_SDK_ROOT`, `ANDROID_NDK_ROOT`, `JAVA_HOME`
2. **Explicit paths** in `[tool.kivy-school.android]` (`sdk_path`, `ndk_path`, `java_path`)
3. **ksproject-managed install** — Downloads and installs to `.kivyschool/` (local or global)

### Assets

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `icon` | `string` (path) | Built-in default | Path to app icon PNG. Copied to `app/src/main/res/mipmap/ic_launcher.png`. |
| `presplash` | `string` (path) | Built-in default | Path to splash screen image. |

### Permissions

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `permissions` | `list[string]` | `[]` | Android permissions to add to the manifest. Use short names without the `android.permission.` prefix. |

```toml
permissions = [
    "INTERNET",
    "ACCESS_FINE_LOCATION",
    "CAMERA",
    "WRITE_EXTERNAL_STORAGE",
]
```

These are merged with permissions declared by any installed [plugin packages](../plugins/overview.md).

### Gradle Dependencies

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `gradle_dependencies` | `list[string]` | `[]` | Maven/Gradle dependency coordinates to add to `app/build.gradle.kts`. |

```toml
gradle_dependencies = [
    "com.google.firebase:firebase-analytics:21.0.0",
    "androidx.camera:camera-core:1.3.0",
]
```

These are merged with dependencies declared by any installed [plugin packages](../plugins/overview.md).

### Meta-Data

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `meta_data` | `dict[string, string]` | `{}` | Extra `<meta-data>` tags injected into the Android manifest's `<application>` element. |

```toml
[tool.kivy-school.android.meta_data]
"com.google.firebase.messaging.default_notification_channel_id" = "default_channel"
```

### Background Services

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `services` | `list[table]` | `[]` | Background services to register in the Android manifest and generate Java/native bridge code for. |

Each service entry:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Java class name for the service (e.g., `LocationService`) |
| `entrypoint` | `string` | Yes | Python module path to run in the service (e.g., `myapp.services.location`) |
| `foreground` | `bool` | No | Whether this is a foreground service (shows persistent notification). Default: `false` |
| `foreground_service_type` | `string` | No | Required for foreground services on Android 14+. Values: `location`, `dataSync`, `camera`, `mediaPlayback`, etc. |

```toml
[[tool.kivy-school.android.services]]
name = "LocationService"
entrypoint = "myapp.services.location"
foreground = true
foreground_service_type = "location"

[[tool.kivy-school.android.services]]
name = "SyncService"
entrypoint = "myapp.services.sync"
foreground = false
```

---

## iOS Configuration

```toml
[tool.kivy-school.ios]
bundle_id = "org.example.myapp"
permissions = ["NSCameraUsageDescription"]
frameworks = ["AVFoundation"]

[tool.kivy-school.ios.info_plist]
CFBundleDisplayName = "My App"
UIRequiresFullScreen = true

[tool.kivy-school.ios.entitlements]
"com.apple.developer.healthkit" = true
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `bundle_id` | `string` | **Required** | iOS bundle identifier (e.g., `com.company.appname`). Must be unique on the App Store. |
| `permissions` | `list[string]` | `[]` | iOS privacy permission keys to include in Info.plist (e.g., `NSCameraUsageDescription`). |
| `frameworks` | `list[string]` | `[]` | Additional system frameworks to link against (e.g., `AVFoundation`, `CoreLocation`). |
| `info_plist` | `dict` | `{}` | Extra key-value pairs merged into the generated Info.plist. |
| `entitlements` | `dict` | `{}` | Entitlements for code signing (e.g., push notifications, HealthKit). |

---

## macOS Configuration

```toml
[tool.kivy-school.macos]
bundle_id = "org.example.myapp"

[tool.kivy-school.macos.info_plist]
LSMinimumSystemVersion = "13.0"

[tool.kivy-school.macos.entitlements]
"com.apple.security.network.client" = true
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `bundle_id` | `string` | **Required** | macOS bundle identifier. |
| `info_plist` | `dict` | `{}` | Extra Info.plist entries for the macOS target. |
| `entitlements` | `dict` | `{}` | macOS entitlements (sandbox, network, files, etc.). |

---

## UV Configuration

ksproject projects use [uv](https://docs.astral.sh/uv/) as the package manager. The generated pyproject.toml includes:

```toml
[tool.uv]
extra-index-url = [
    "https://pypi-index.psychowaspx.workers.dev/simple/",
    "https://pypi.anaconda.org/kivyschool/simple",
]
```

| Channel | Purpose |
|---------|---------|
| `pypi-index.psychowaspx.workers.dev` | Cross-compiled Python wheels (CPython, PySwiftKit) for iOS/macOS |
| `kivyschool/simple` | Pre-built wheels for Android (libpython, Kivy, SDL2) |

These channels provide the pre-compiled native wheels that ksproject uses when installing site-packages for mobile platforms.

---

## Complete Example

Here's a full `pyproject.toml` for a real-world app with location services, Firebase, and camera:

```toml
[project]
name = "myapp"
version = "1.0.0"
description = "A location-aware Kivy app"
requires-python = ">=3.13"
dependencies = [
    "kivy>=2.3.1,<3.0.0",
    "requests>=2.31.0",
]

[project.scripts]
myapp = "myapp:main"

[tool.uv]
extra-index-url = [
    "https://pypi-index.psychowaspx.workers.dev/simple/",
    "https://pypi.anaconda.org/kivyschool/simple",
]

[tool.kivy-school]
app_name = "Location Tracker"

[tool.kivy-school.android]
package_name = "com.mycompany.locationtracker"
archs = ["arm64-v8a", "x86_64"]
api = 36
min_api = 26
permissions = [
    "INTERNET",
    "ACCESS_FINE_LOCATION",
    "ACCESS_COARSE_LOCATION",
    "FOREGROUND_SERVICE",
    "FOREGROUND_SERVICE_LOCATION",
    "CAMERA",
]
gradle_dependencies = [
    "com.google.firebase:firebase-analytics:21.0.0",
    "com.google.android.gms:play-services-location:21.0.1",
]
icon = "assets/icon.png"

[tool.kivy-school.android.meta_data]
"com.google.firebase.messaging.default_notification_channel_id" = "tracking"

[[tool.kivy-school.android.services]]
name = "LocationTracker"
entrypoint = "myapp.services.tracker"
foreground = true
foreground_service_type = "location"

[tool.kivy-school.ios]
bundle_id = "com.mycompany.locationtracker"
permissions = [
    "NSLocationWhenInUseUsageDescription",
    "NSLocationAlwaysUsageDescription",
    "NSCameraUsageDescription",
]
frameworks = ["CoreLocation", "AVFoundation"]

[tool.kivy-school.ios.entitlements]
"com.apple.developer.location.push" = true

[tool.kivy-school.macos]
bundle_id = "com.mycompany.locationtracker"

[build-system]
requires = ["uv_build>=0.11.3,<0.12.0"]
build-backend = "uv_build"
```
