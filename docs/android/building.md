# Build & Run on Android

This guide covers building your ksproject app into an APK (or AAB), signing it, and running it on an emulator or physical device.

---

## Overview

The Android build pipeline:

1. **Pre-build hook** — Your `pre_build` script runs (if configured)
2. **Resolve toolchain** — SDK, NDK, Java are downloaded/located automatically
3. **Install site-packages** — Cross-compiled Python packages installed per target architecture
4. **Collect plugin configs** — `.gradle/*.json` files from installed packages are merged
5. **Generate Gradle project** — Complete Android project written to `project_dist/gradle/` by the [bootstrap](../configuration/pyproject-toml.md#root-configuration)
6. **Gradle assemble** — `./gradlew assembleDebug` (or `Release`) stages, optimizes, and packages the APK

---

## First Build

On first build, ksproject automatically installs everything needed:

```bash
uv run ksproject android build
```

This will:

- Download **Android command-line tools** from Google
- Install **SDK platform**, **build-tools**, **NDK**, **CMake** via sdkmanager
- Download **Java 21** via sdkman (if no compatible JDK found)
- Download **CPython for Android** (pre-built from the KivySchool index)
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
uv run ksproject android build
# or explicitly:
uv run ksproject android build debug
```

Produces: `project_dist/gradle/app/build/outputs/apk/debug/app-debug.apk`

### Release Build

```bash
uv run ksproject android build release
```

Produces: `project_dist/gradle/app/build/outputs/apk/release/app-release-unsigned.apk` (unsigned — see [Signing](#signing-for-release) below).

### Android App Bundle (AAB)

For Google Play Store distribution:

```bash
uv run ksproject android build release --bundle
```

Produces: `project_dist/gradle/app/build/outputs/bundle/release/app-release.aab`

### Android Archive (AAR)

For library distribution:

```bash
uv run ksproject android build --aar
```

Produces an AAR library instead of an APK.

### Clean Build

```bash
uv run ksproject android build --clean
```

---

## Signing for Release

Play Store uploads require signed artifacts. ksproject wraps `keytool`, `apksigner`, and `jarsigner` so you never have to locate them yourself.

### 1. Generate a Keystore (once)

```bash
uv run ksproject android genkey \
    --out my-release-key.jks \
    --storepass SecretPass123 \
    --keyalias myapp
```

Optional: `--keypass` (defaults to the store password) and `--dname "CN=My App, O=My Org"`.

### 2. Sign the Artifact

```bash
# Sign the release APK
uv run ksproject android sign \
    --keystore my-release-key.jks --storepass SecretPass123 --keyalias myapp

# Sign the release AAB instead
uv run ksproject android sign --bundle \
    --keystore my-release-key.jks --storepass SecretPass123 --keyalias myapp
```

Signing produces `app-release-signed.apk` / `app-release-signed.aab` next to the original.

### Credentials via .env

All flags fall back to environment variables, which ksproject loads from the project's `.env` file (created by `ksproject init`, gitignored):

```bash
KEYSTORE="my-release-key.jks"
STOREPASS="SecretPass123"
KEYALIAS="myapp"
# KEYPASS defaults to STOREPASS
```

With `.env` filled in, signing is just `uv run ksproject android sign`.

### Play Store CI Workflow

```bash
uv run ksproject android create-action
```

Writes a **tag-triggered GitHub Actions workflow** that builds, signs, and uploads an AAB to the Play Store. Configure these repository secrets: `ANDROID_KEYSTORE_BASE64`, `STOREPASS`, `KEYALIAS`, `KEYPASS`, and `PLAY_SERVICE_ACCOUNT_JSON`.

---

## Run on Device or Emulator

### List Available Devices

```bash
uv run ksproject android devices
```

This shows both:

- **ADB-connected devices** (physical phones/tablets connected via USB or Wi-Fi)
- **Available AVDs** (Android Virtual Devices / emulators)

### Run on a Specific Device

```bash
# By AVD name — boots the emulator and waits for it
uv run ksproject android run --name "Pixel_8_API_36"

# By adb serial of a device or already-running emulator
uv run ksproject android run --uuid "emulator-5554"
```

The `run` command will:

1. Find the existing APK (does **not** rebuild)
2. Boot the emulator if you passed `--name` and it isn't running
3. Install the APK via `adb install`
4. Launch the main activity

!!! warning "Build before running"
    The `run` command only installs and launches — it does not build. Always run `uv run ksproject android build` first if you've made changes.

### Specifying Build Variant

```bash
uv run ksproject android run --name "Pixel_8" --variant release
```

For the release variant, `run` prefers a signed APK (`app-release-signed.apk`), then a standard one, then the unsigned artifact.

---

## Creating an Emulator

If you don't have a physical device, create an AVD:

```bash
# Get the path to the SDK tools
uv run ksproject android get-path sdk

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
uv run ksproject android get-path sdk

# Android NDK location
uv run ksproject android get-path ndk

# Emulator binary location
uv run ksproject android get-path emulator
```

---

## Generated Project Structure

After `uv run ksproject android build`, the `project_dist/gradle/` directory contains a complete Android Studio-compatible project:

```
project_dist/gradle/
├── app/
│   ├── build.gradle.kts          # App module (from your build.tmpl.gradle.kts)
│   └── src/main/
│       ├── AndroidManifest.xml   # Generated from AndroidManifest.tmpl.xml + config
│       ├── java/                 # Java sources
│       │   ├── org/example/myapp/
│       │   │   ├── MainActivity.java
│       │   │   ├── KivyPythonActivity.java
│       │   │   └── <YourService>.java     # one per configured service
│       │   └── org/libsdl/app/            # SDL2 Java (SDLActivity, ...)
│       ├── cpp/                  # Native bootstrap
│       │   ├── CMakeLists.txt
│       │   ├── main.c            # SDL_main → CPython entry point
│       │   ├── service_main.c    # Entry point for background services
│       │   ├── python_include/   # CPython headers per ABI
│       │   └── sdl2_include/     # SDL2 headers
│       ├── jniLibs/              # Native libraries per ABI
│       │   └── arm64-v8a/
│       │       ├── libpython3.so
│       │       └── lib*.so       # supporting native libraries
│       ├── assets/
│       │   ├── python3.13/       # Pure-Python standard library
│       │   └── lib-dynload/      # C extension modules per ABI
│       └── res/
│           ├── mipmap/ic_launcher.png
│           └── drawable/         # presplash image (or raw/ for Lottie)
├── site_packages/                # Cross-compiled Python packages per ABI
│   └── arm64-v8a/
├── build.gradle.kts              # Root Gradle plugins (+ your gradle_plugins)
├── settings.gradle.kts           # Repository config
├── gradle.properties             # JVM settings
├── local.properties              # SDK path reference
├── gradlew                       # Gradle wrapper script
└── gradle/
    └── wrapper/
        └── gradle-wrapper.jar
```

At build time, Gradle **stages** `site_packages/<abi>`, the stdlib, and `lib-dynload` together, runs the [optimization pass](#size-optimizations), and packs the result into a single compressed `assets.zip` inside the APK.

### Key Build Details

| Component | Version | Notes |
|-----------|---------|-------|
| Gradle | 9.5.0 | Downloaded automatically |
| Android Gradle Plugin | 8.9.1 | Configured in `build.gradle.kts` |
| CMake | 3.22.1 | For native code compilation |
| SDL2 | 2.30.11 | Java files + native headers |
| CPython | 3.13 (default) | Pre-built from the KivySchool index; pin via [`.python-version`](../configuration/pyproject-toml.md#python-version) |

### Customizing the Templates

Two files in your **project root** are templates for the generated project — edit them and rebuild:

- **`AndroidManifest.tmpl.xml`** — the manifest skeleton. Permissions, meta-data, and services from your config are injected into it.
- **`build.tmpl.gradle.kts`** — the app module's `build.gradle.kts` skeleton, with `{{ placeholder }}` slots that ksproject fills in (package name, SDK levels, ABI filters, dependencies...). Add custom Gradle logic here; it survives regeneration, unlike edits to the generated files in `project_dist/`.

---

## Size Optimizations

Before packaging, an optimization Gradle task runs over the staged Python content:

- **Byte-compilation** — everything is compiled to `.pyc` (optimization level 2) and the `.py` sources are dropped. Always on for **release** builds; controlled by [`byte_compile_python`](../configuration/pyproject-toml.md#byte-compilation) for debug builds (or force it once with `./gradlew -PforceCompile`). The compiling interpreter is a uv-managed Python matching the bundled runtime, so `.pyc` magic numbers always match.
- **Junk stripping** — `tests/`, `docs/`, `examples/`, caches, and source-only files (`.pyi`, `.c`, `.h`, `.pyx`, `.md`, `.rst`, ...) are removed from the bundled packages.
- **Symbol stripping** — all bundled `.so` files are stripped with the NDK's `llvm-strip`.
- **Zip packing** — the result ships as one compressed `assets.zip` instead of thousands of loose asset files.

Your [`post_build` hook](../configuration/pyproject-toml.md#build-hooks) runs on the staged content after these steps, right before AGP packages it.

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

The `x86_64` arch is useful for running on Intel-based emulators, but roughly doubles the APK size.

---

## Toolchain Storage

Where ksproject stores downloaded tools:

=== "Global (`global_tools = true`, generated default)"

    ```
    ~/.kivyschool/
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

=== "Project-Local (`global_tools = false`)"

    ```
    myapp/.kivyschool/
    ├── android-sdk/
    │   └── ... (same structure)
    ├── Python-3.13.8/
    │   └── ...
    └── sdl2-2.30.11/
    ```

!!! tip "Global tools are shared"
    New projects are generated with `global_tools = true`, sharing the SDK/NDK across all your projects (~2GB saved per additional project). Set it to `false` for a fully self-contained project directory.

---

## Environment Variables

These environment variables override ksproject's toolchain resolution:

| Variable | Effect |
|----------|--------|
| `ANDROID_HOME` / `ANDROID_SDK_ROOT` | Use this SDK instead of downloading |
| `ANDROID_NDK_ROOT` | Use this NDK instead of downloading (ignored if you pin an `ndk` version) |
| `JAVA_HOME` | Use this JDK (must be 17–21) |
| `KIVYSCHOOL_PREBUILT_INDEX` | Custom index URL for pre-built CPython wheels |
| `KIVYSCHOOL_PREBUILT_BUILD` | Override CPython build number |
| `KIVYSCHOOL_PREBUILT_API` | Override CPython target API |
| `KIVYSCHOOL_PREBUILT_DISABLE=1` | Skip the pre-built CPython and build from source |
| `KIVYSCHOOL_PREBUILT_FILE_<ARCH>` | Point at a local CPython wheel file (e.g. `KIVYSCHOOL_PREBUILT_FILE_ARM64_V8A=/path/to.whl`) |
| `KEYSTORE` / `STOREPASS` / `KEYALIAS` / `KEYPASS` | Signing credentials (usually set in `.env`) |

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
