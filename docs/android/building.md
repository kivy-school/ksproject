# Build & Run on Android

This guide covers building your ksproject app into an APK (or AAB) and running it on an emulator or physical device.

---

## Overview

The Android build pipeline:

1. **Resolve toolchain** — SDK, NDK, Java are downloaded/located automatically
2. **Install site-packages** — Cross-compiled Python packages installed per target architecture
3. **Collect plugin configs** — `.gradle/*.json` files from installed packages are merged
4. **Generate Gradle project** — Complete Android project written to `project_dist/gradle/`
5. **Gradle assemble** — `./gradlew assembleDebug` (or `Release`) produces the APK

---

## First Build

On first build, ksproject automatically installs everything needed:

```bash
ksproject android build
```

This will:

- Download **Android command-line tools** from Google
- Install **SDK platform**, **build-tools**, **NDK**, **CMake** via sdkmanager
- Download **Java 21** via sdkman (if no compatible JDK found)
- Download **CPython for Android** (pre-built from kivyschool channel)
- Download **SDL2** source (for Java files and native headers)
- Download **Gradle wrapper** (v9.5.0)
- Cross-compile install your project's Python dependencies for `arm64-v8a`
- Generate the full Gradle project
- Build the debug APK

!!! info "First build takes time"
    The initial build downloads ~2GB of toolchain files. Subsequent builds reuse the cached tools and only rebuild what changed.

---

## Build Commands

### Debug Build (default)

```bash
ksproject android build
# or explicitly:
ksproject android build debug
```

Produces: `project_dist/gradle/app/build/outputs/apk/debug/app-debug.apk`

### Release Build

```bash
ksproject android build release
```

Produces: `project_dist/gradle/app/build/outputs/apk/release/app-release-unsigned.apk`

### Android App Bundle (AAB)

For Google Play Store distribution:

```bash
ksproject android build release --bundle
```

Produces: `project_dist/gradle/app/build/outputs/bundle/release/app-release.aab`

### Android Archive (AAR)

For library distribution:

```bash
ksproject android build --aar
```

Produces an AAR library instead of an APK.

---

## Run on Device or Emulator

### List Available Devices

```bash
ksproject android devices
```

This shows both:

- **ADB-connected devices** (physical phones/tablets connected via USB or Wi-Fi)
- **Available AVDs** (Android Virtual Devices / emulators)

### Run on a Specific Device

```bash
# By device name (AVD name or device serial)
ksproject android run --name "Pixel_8_API_36"

# By UUID/serial
ksproject android run --uuid "emulator-5554"
```

The `run` command will:

1. Find the existing APK (does **not** rebuild)
2. Install the APK via `adb install`
3. Launch the main activity

!!! warning "Build before running"
    The `run` command only installs and launches — it does not build. Always run `ksproject android build` first if you've made changes.

### Specifying Build Variant

```bash
ksproject android run --name "Pixel_8" --variant release
```

---

## Creating an Emulator

If you don't have a physical device, create an AVD:

```bash
# Get the path to the SDK tools
ksproject android get-path sdk

# Use avdmanager to create a device
$SDK_PATH/cmdline-tools/latest/bin/avdmanager create avd \
    --name "Pixel_8_API_36" \
    --package "system-images;android-36;google_apis;arm64-v8a" \
    --device "pixel_8"
```

ksproject's SDK installation includes the system image for your configured `sdk` version and architectures.

---

## Toolchain Paths

Query where ksproject installed (or found) the Android tools:

```bash
# Android SDK location
ksproject android get-path sdk

# Android NDK location
ksproject android get-path ndk

# Emulator binary location
ksproject android get-path emulator
```

---

## Generated Project Structure

After `ksproject android build`, the `project_dist/gradle/` directory contains a complete Android Studio-compatible project:

```
project_dist/gradle/
├── app/
│   ├── build.gradle.kts          # App module config
│   └── src/main/
│       ├── AndroidManifest.xml   # Generated from template + config
│       ├── java/                 # Java sources
│       │   └── org/example/myapp/
│       │       └── MainActivity.java
│       ├── cpp/                  # Native bootstrap
│       │   ├── CMakeLists.txt
│       │   ├── main.c            # SDL_main → CPython entry point
│       │   └── python_include/   # CPython headers
│       ├── jniLibs/              # Native libraries per ABI
│       │   └── arm64-v8a/
│       │       └── libpython3.13.so
│       ├── assets/               # Python runtime + app code
│       │   ├── python3.13/       # Standard library
│       │   ├── lib-dynload/      # Extension modules per ABI
│       │   └── site_packages/    # Your app + dependencies per ABI
│       └── res/
│           └── mipmap/
│               └── ic_launcher.png
├── build.gradle.kts              # Root Gradle plugins
├── settings.gradle.kts           # Repository config
├── gradle.properties             # JVM settings
├── local.properties              # SDK path reference
├── gradlew                       # Gradle wrapper script
└── gradle/
    └── wrapper/
        └── gradle-wrapper.jar
```

### Key Build Details

| Component | Version | Notes |
|-----------|---------|-------|
| Gradle | 9.5.0 | Downloaded automatically |
| Android Gradle Plugin | 8.9.1 | Configured in `build.gradle.kts` |
| CMake | 3.22.1 | For native code compilation |
| SDL2 | 2.30.11 | Java files + native headers |
| CPython | 3.13 | Pre-built from kivyschool channel |

---

## Multi-Architecture Builds

By default, ksproject builds for `arm64-v8a` only (covers most modern devices). To target multiple architectures:

```toml
[tool.kivy-school.android]
archs = ["arm64-v8a", "x86_64"]
```

Each architecture gets:

- Its own cross-compiled site-packages
- Its own `jniLibs/<abi>/` directory with native `.so` files
- Its own lib-dynload directory in assets

The `x86_64` arch is useful for running on Intel-based emulators with better performance.

---

## Toolchain Storage

Where ksproject stores downloaded tools:

=== "Project-Local (default)"

    ```
    myapp/.kivyschool/
    ├── android-sdk/
    │   ├── cmdline-tools/latest/
    │   ├── platforms/android-36/
    │   ├── build-tools/36.0.0/
    │   ├── ndk/28.2.13676358/
    │   ├── emulator/
    │   └── cmake/3.22.1/
    ├── Python-3.13.8/
    │   └── cross-build/<triple>/prefix/
    └── sdl2-2.30.11/
    ```

=== "Global (`global_tools = true`)"

    ```
    ~/.kivyschool/
    ├── android-sdk/
    │   └── ... (same structure)
    ├── Python-3.13.8/
    │   └── ...
    └── sdl2-2.30.11/
    ```

!!! tip "Use global tools for multiple projects"
    Set `global_tools = true` in your config to share the SDK/NDK across all projects. This saves ~2GB of disk space per additional project.

---

## Environment Variables

These environment variables override ksproject's toolchain resolution:

| Variable | Effect |
|----------|--------|
| `ANDROID_HOME` / `ANDROID_SDK_ROOT` | Use this SDK instead of downloading |
| `ANDROID_NDK_ROOT` | Use this NDK instead of downloading |
| `JAVA_HOME` | Use this JDK (must be 17–21) |
| `KIVYSCHOOL_PREBUILT_INDEX` | Custom index URL for pre-built CPython wheels |
| `KIVYSCHOOL_PREBUILT_BUILD` | Override CPython build number |
| `KIVYSCHOOL_PREBUILT_API` | Override CPython target API |

---

## Troubleshooting

### Java Version Issues

ksproject requires **Java 17–21**. Java 22+ causes `sdkmanager` to crash.

```bash
# Check your Java version
java -version

# If you have Java 22+, set java_path to a compatible JDK:
```

```toml
[tool.kivy-school.android]
java_path = "/usr/lib/jvm/java-21-openjdk"
```

Or let ksproject install Java 21 automatically via sdkman.

### SDK License Acceptance

On first SDK install, ksproject automatically accepts all Android SDK licenses. No manual intervention needed.

### Emulator Won't Start

Make sure your system supports hardware acceleration:

- **Linux**: KVM must be enabled (`/dev/kvm` accessible)
- **macOS**: Hypervisor.framework (Apple Silicon native) or HAXM (Intel)
- **Windows**: WHPX or HAXM
