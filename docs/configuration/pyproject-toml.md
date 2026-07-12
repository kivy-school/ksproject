# pyproject.toml Reference

All ksproject configuration lives under `[tool.kivy-school]` in your `pyproject.toml`. This page documents every available key, its type, default value, and behavior.

---

## Root Configuration

```toml
[tool.kivy-school]
app_name = "My App"
bootstrap = "kivy"
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `app_name` | `string` | Project name from `[project]` | Display name of your application. Used as the app label on Android and the bundle display name on iOS/macOS. |
| `bootstrap` | `string` | `"kivy"` | Which bootstrap generates the native projects. Bootstraps live in the [ksp-bootstraps](https://github.com/kivy-school/ksp-bootstraps) package; `kivy` is currently the only shipped bootstrap. |

---

## Python Version

The bundled CPython version is controlled by your project's `.python-version` file, not by a `[tool.kivy-school]` key:

- **No file, or a bare `3.13`** — ksproject uses its built-in default patch release.
- **An exact pin like `3.13.11`** — that exact version drives the Android CPython build, the iOS/macOS Python.xcframework, and the interpreter used to byte-compile your app.

Supported exact versions are gated by BeeWare's Python-Apple-support releases: `3.13.8`, `3.13.11`, `3.13.14`, `3.14.2`, `3.14.6`. Anything else fails fast with an error before any downloads happen.

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
global_tools = true
permissions = ["INTERNET", "CAMERA"]
gradle_dependencies = [
    "com.google.firebase:firebase-analytics:21.0.0",
]
```

### Identity & Versioning

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `package_name` | `string` | **Required** | Java package name (e.g., `org.example.myapp`). Used as the Android application ID and Java package namespace. |
| `archs` | `list[string]` | `["arm64-v8a"]` | Target CPU architectures. Valid values: `arm64-v8a`, `x86_64`. Each arch gets its own site-packages with cross-compiled native extensions. |
| `version_name` | `string` | `"1.0"` | User-visible version string (`versionName` in Gradle). Change it when you release a new version. |
| `version_code` | `int` | `1` | Monotonic build number (`versionCode` in Gradle). Increase it for every update you upload to a store. |

### SDK & NDK Versions

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api` | `int` | `36` | **Compile SDK version** (also used as target SDK). Determines which Android API level your app compiles against. |
| `min_api` | `int` | `24` | **Minimum SDK version**. The lowest Android version your app supports (Android 7.0 = API 24). |
| `sdk` | `string` | `"36"` | SDK platform version string. Used in SDK paths like `platforms;android-{sdk}` and `system-images;android-{sdk};google_apis;{arch}`. |
| `ndk` | `string` | `"28c"` | NDK version shorthand. Mapped internally to full version strings (e.g., `28c` → `28.2.13676358`). If the requested version isn't present, ksproject installs it. |
| `ndk_api` | `int` | `24` | Native (C/C++) API level. The minimum Android version for native code. Usually matches `min_api`. |

!!! info "API vs SDK"
    `api` is an integer used for `compileSdk`/`targetSdk` in Gradle. `sdk` is a string used in SDK manager paths. They typically have the same numeric value but serve different purposes — never cast between them.

### Tool Paths

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `sdk_path` | `string` (path) | Auto-resolved | Override the Android SDK location. Skips automatic SDK download/installation. |
| `ndk_path` | `string` (path) | Auto-resolved | Override the NDK location. Skips automatic NDK download. |
| `java_path` | `string` (path) | Auto-resolved | Override the Java/JDK location. Must be Java 17–21 (Java 22+ crashes sdkmanager). |
| `global_tools` | `bool` | `false` | When `true`, installs SDK/NDK/Java to `~/.kivyschool/` (shared across projects). When `false`, uses `<project>/.kivyschool/` (project-local). New projects are generated with `global_tools = true`. |
| `global_tools_path` | `string` (path) | `~/.kivyschool` | Override the global tools directory when `global_tools = true`. |

### Tool Resolution Priority

ksproject resolves SDK/NDK/Java locations in this order:

1. **Environment variables** — `ANDROID_HOME` / `ANDROID_SDK_ROOT`, `ANDROID_NDK_ROOT`, `JAVA_HOME`
2. **Explicit paths** in `[tool.kivy-school.android]` (`sdk_path`, `ndk_path`, `java_path`)
3. **ksproject-managed install** — Downloads and installs to `.kivyschool/` (local or global)

The one exception: if you pin a specific `ndk` version, that version is installed and used even when an environment variable points at a different NDK.

### Assets & Splash Screen

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `icon` | `string` (path) | Built-in default | Path to app icon PNG (relative to `pyproject.toml`). Copied to `app/src/main/res/mipmap/ic_launcher.png`. |
| `presplash` | `string` (path) | Built-in default | Splash screen image (`png`, `jpg`, or animated `gif`). |
| `presplash_color` | `string` | `"#FFFFFF"` | Background color shown behind/around the splash asset. |
| `presplash_lottie` | `string` (path) | — | A [Lottie](https://airbnb.io/lottie/) animation JSON to use as the splash screen. Takes precedence over `presplash` and automatically adds the `com.airbnb.android:lottie` Gradle dependency. |

### Permissions

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `permissions` | `list[string]` | `[]` | Android permissions to add to the manifest. Use short names without the `android.permission.` prefix. |

```toml
permissions = [
    "INTERNET",
    "ACCESS_FINE_LOCATION",
    "CAMERA",
    "POST_NOTIFICATIONS",
]
```

These are merged with permissions declared by any installed [plugin packages](../plugins/overview.md). If the merged list is empty, the manifest gets `INTERNET` as a baseline.

### Gradle Dependencies & Plugins

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `gradle_dependencies` | `list[string]` | `[]` | Maven/Gradle dependency coordinates added to `app/build.gradle.kts` as `implementation(...)`. |
| `gradle_plugins` | `list[string]` | `[]` | Full plugin declaration lines added to the root `build.gradle.kts` `plugins {}` block. |

```toml
gradle_dependencies = [
    "com.google.firebase:firebase-analytics:21.0.0",
    "androidx.camera:camera-core:1.3.0",
]
gradle_plugins = [
    'id("com.google.gms.google-services") version "4.4.2" apply false',
]
```

Dependencies are merged with those declared by any installed [plugin packages](../plugins/overview.md).

### Meta-Data

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `meta_data` | `dict[string, string]` | `{}` | Extra `<meta-data>` tags injected into the Android manifest's `<application>` element. |

```toml
[tool.kivy-school.android.meta_data]
"com.google.firebase.messaging.default_notification_channel_id" = "default_channel"
```

### Including Extra Files

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `include_files` | `list` | `[]` | Copy extra files (e.g. `google-services.json`) into the generated project. Each entry is a destination directory **relative to `project_dist/`** followed by one or more source paths (relative to `pyproject.toml`; globs allowed). |

Two equivalent formats:

```toml
# Format 1: Flat list (destination, source 1, source 2, ...)
include_files = [
    ["gradle/app", "./google-services.json", "./some-other-config.xml"]
]

# Format 2: Nested list (destination, [sources])
include_files = [
    ["gradle/app", ["./google-services.json", "./some-other-config.xml"]]
]
```

### Build Hooks

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `pre_build` | `string` (path) | — | Script run **before** site-packages are installed. `.py` scripts run via `uv run`; anything else is executed directly. Receives a `WHEELHOUSE` environment variable pointing at your project's [wheelhouse](../wheelhouse/overview.md). |
| `post_build` | `string` (path) | — | Script run as a Gradle task on the **staged app content** (assets, jniLibs, sources) after staging but before Gradle packages the APK/AAB — the place to prune or transform bundled files. |

### Byte-Compilation

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `byte_compile_python` | `bool` | `true` | Byte-compile all bundled Python (stdlib, site-packages, your app) to `.pyc` and drop the `.py` sources in **debug** builds. **Release builds always byte-compile**, regardless of this setting. |

Byte-compilation uses a uv-managed interpreter matching the bundled CPython version, so `.pyc` magic numbers always match the runtime. See [Build & Run on Android](../android/building.md#size-optimizations) for what else the optimization pass does.

### Background Services

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `services` | `list[table]` | `[]` | Background services to register in the Android manifest and generate Java bridge code for. |

Each service entry:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Java class name for the service (e.g., `LocationService`) |
| `entrypoint` | `string` | Yes | Python module path to run in the service (e.g., `myapp.services.location`) |
| `foreground` | `bool` | No | Whether this is a foreground service (shows persistent notification). Default: `false` |
| `foreground_service_type` | `string` | No | Required for foreground services on Android 14+. Values: `location`, `dataSync`, `camera`, `mediaPlayback`, etc. |
| `start_type` | `string` | No | Restart behavior when the service is killed. Default: `"START_NOT_STICKY"` |
| `notification_title` | `string` | No | Foreground notification title. Default: `"<name> is running"` |
| `notification_text` | `string` | No | Foreground notification body. Default: `"Background task active"` |
| `notification_icon` | `string` | No | Android system icon name for the notification. Default: `"stat_notify_sync"` |

```toml
[[tool.kivy-school.android.services]]
name = "LocationService"
entrypoint = "myapp.services.location"
foreground = true
foreground_service_type = "location"
notification_title = "Tracking location"
notification_text = "Location updates are active"

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
developer_team = "ABC123XYZ"

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
| `developer_team` | `string` | — | Your Apple Developer Team ID. Enables automatic code signing and is required for App Store archives. Omit for manual signing in Xcode. |
| `minimum_deployment` | `string` | `"15.6"` | Minimum iOS version your app supports (`IPHONEOS_DEPLOYMENT_TARGET`). |
| `pre_build` | `string` (path) | — | Script run before site-packages are installed, same semantics as the [Android hook](#build-hooks). |
| `post_build` | `string` (path) | — | Reserved for post-build processing. |

For deeper Xcode project customization (SPM packages, build settings, extra targets), use an [`xcode.yaml` overlay](../ios/building.md#customizing-the-spec-xcodeyaml) — it's merged into the generated XcodeGen spec.

---

## macOS Configuration

```toml
[tool.kivy-school.macos]
bundle_id = "org.example.myapp"
developer_team = "ABC123XYZ"

[tool.kivy-school.macos.info_plist]
LSMinimumSystemVersion = "13.0"

[tool.kivy-school.macos.entitlements]
"com.apple.security.network.client" = true
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `bundle_id` | `string` | **Required** | macOS bundle identifier. |
| `info_plist` | `dict` | `{}` | Extra Info.plist entries for the macOS target. When both iOS and macOS declare the same key, the macOS value wins for shared plist entries. |
| `entitlements` | `dict` | `{}` | macOS entitlements (sandbox, network, files, etc.). |
| `developer_team` | `string` | — | Apple Developer Team ID for automatic signing / App Store archives. |
| `minimum_deployment` | `string` | `"11.5"` | Minimum macOS version your app supports (`MACOSX_DEPLOYMENT_TARGET`). |
| `pre_build` | `string` (path) | — | Script run before site-packages are installed. |
| `post_build` | `string` (path) | — | Reserved for post-build processing. |

---

## UV Configuration

ksproject projects use [uv](https://docs.astral.sh/uv/) as the package manager. The generated pyproject.toml includes:

```toml
[tool.uv]
index-strategy = "unsafe-best-match"
find-links = ["./wheelhouse"]

[tool.uv.pip]
extra-index-url = [
    "https://pypi-index.psychowaspx.workers.dev/simple",
    "https://pypi.anaconda.org/kivyschool/simple",
]
find-links = ["./wheelhouse"]
```

| Source | Purpose |
|--------|---------|
| KivySchool indexes (`extra-index-url`) | Pre-built cross-compiled wheels: Kivy for Android/iOS/macOS, CPython builds |
| `./wheelhouse` (`find-links`) | Your [local wheel repository](../wheelhouse/overview.md) — any wheel you drop there becomes a candidate |
| `index-strategy = "unsafe-best-match"` | Considers all sources and picks the best platform-matching wheel, instead of stopping at the first index that knows the package name |

---

## Environment Variables (.env)

`ksproject init` creates a `.env` file (gitignored) that ksproject loads on every invocation. It's the standard place for signing credentials so you don't pass them on the command line:

```bash
# ONESIGNAL_APP_ID=""
# KEYSTORE=""
# KEYALIAS=""
# STOREPASS=""
# KEYPASS="defaults_to_storepass"
```

`ksproject android sign` and `ksproject android genkey` fall back to these variables when their flags are omitted. App Store uploads similarly fall back to `ASC_KEY_ID`, `ASC_ISSUER_ID`, and `ASC_KEY_PATH`.

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
index-strategy = "unsafe-best-match"
find-links = ["./wheelhouse"]

[tool.uv.pip]
extra-index-url = [
    "https://pypi-index.psychowaspx.workers.dev/simple",
    "https://pypi.anaconda.org/kivyschool/simple",
]
find-links = ["./wheelhouse"]

[tool.kivy-school]
app_name = "Location Tracker"
bootstrap = "kivy"

[tool.kivy-school.android]
package_name = "com.mycompany.locationtracker"
version_name = "1.0"
version_code = 3
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
gradle_plugins = [
    'id("com.google.gms.google-services") version "4.4.2" apply false',
]
include_files = [
    ["gradle/app", "./google-services.json"],
]
icon = "assets/icon.png"
presplash_color = "#101020"
byte_compile_python = true

[tool.kivy-school.android.meta_data]
"com.google.firebase.messaging.default_notification_channel_id" = "tracking"

[[tool.kivy-school.android.services]]
name = "LocationTracker"
entrypoint = "myapp.services.tracker"
foreground = true
foreground_service_type = "location"

[tool.kivy-school.ios]
bundle_id = "com.mycompany.locationtracker"
developer_team = "ABC123XYZ"
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
developer_team = "ABC123XYZ"

[build-system]
requires = ["uv_build>=0.11.3,<0.12.0"]
build-backend = "uv_build"
```
