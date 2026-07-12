# Build & Run on iOS

This guide covers building your ksproject app for iOS and macOS, running it on a simulator or physical device, and archiving for the App Store. All Apple commands live under the `apple` namespace:

| Command group | Purpose |
|---------------|---------|
| `ksproject apple ios ...` | iOS **device** builds, devices, run, archive |
| `ksproject apple sim ...` | iOS **Simulator** builds, devices, run |
| `ksproject apple macos ...` | macOS builds, run, archive |
| `ksproject apple all build` | Build for iOS device + Simulator + macOS in one go |
| `ksproject apple xcode open` | Open the generated project in Xcode |

---

## Overview

The build pipeline (same shape for iOS and macOS):

1. **Generate Xcode project** — folder layout, Swift sources, and an XcodeGen spec written to `project_dist/xcode/` (first build only; Xcode opens automatically)
2. **Install frameworks** — Python.xcframework (BeeWare) installed into `Frameworks/`
3. **Pre-build hook** — your `pre_build` script runs (if configured)
4. **Install site-packages** — cross-compiled Python packages installed per platform slice
5. **Sync xcframeworks** — `.frameworks/` shipped inside wheels are moved to `Frameworks/` and the Xcode project is regenerated if the set changed
6. **xcodebuild** — compiles the app for simulator, device, or macOS

---

## Prerequisites

Apple builds require **macOS** with **Xcode** (and its command-line tools) installed:

```bash
xcode-select --install
```

That's it — ksproject downloads **XcodeGen** automatically (cached in `~/.kivyschool/`), so there's nothing to install via Homebrew.

---

## Build Commands

### Build for Simulator

```bash
uv run ksproject apple sim build
```

Produces an `.app` bundle for the iOS Simulator (arm64 on Apple Silicon, x86_64 on Intel).

### Build for Device

```bash
uv run ksproject apple ios build
```

Produces an `.app` bundle for physical iOS devices (arm64).

### Build for macOS

```bash
uv run ksproject apple macos build
```

Produces a native macOS `.app` that runs directly on your Mac.

### Debug vs Release

Every build command takes an optional variant (default `debug`):

```bash
uv run ksproject apple ios build release
uv run ksproject apple sim build release
uv run ksproject apple macos build release
```

### Everything at Once

```bash
uv run ksproject apple all build [debug|release]
```

Builds iOS device, iOS Simulator, and macOS sequentially.

!!! note "First build opens Xcode"
    The first build generates the Xcode project and opens it in Xcode, so you can watch progress or tweak signing. Built apps land under `project_dist/xcode/build/Build/Products/`.

---

## Run on Simulator or Device

### List Available Targets

```bash
# iOS simulators
uv run ksproject apple sim devices

# Connected physical devices
uv run ksproject apple ios devices
```

Simulators are discovered via `xcrun simctl`, physical devices via `xcrun devicectl`.

### Run on a Simulator

```bash
# By simulator name
uv run ksproject apple sim run --name "iPhone 16 Pro"

# By UUID
uv run ksproject apple sim run --uuid "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
```

The `run` command boots the simulator (if needed), installs the `.app`, and launches it with the app's console streamed to your terminal.

### Run on a Physical Device

Connect your iPhone via USB or Wi-Fi, then:

```bash
uv run ksproject apple ios run --name "My iPhone"
```

!!! note "Code Signing"
    Running on a physical device requires a valid Apple Developer certificate. Set [`developer_team`](../configuration/pyproject-toml.md#ios-configuration) in `[tool.kivy-school.ios]` for automatic signing, or configure signing manually in Xcode. Free developer accounts work for personal testing.

### Run on macOS

```bash
uv run ksproject apple macos run
```

Launches the built `.app` directly (not via `open`), so Python's stdout/stderr stream to your terminal.

---

## Archive & App Store Upload

### Create an Archive

```bash
# iOS (defaults to release)
uv run ksproject apple ios archive

# macOS
uv run ksproject apple macos archive
```

Produces an `.xcarchive` under `project_dist/xcode/archives/`. Archiving requires `developer_team` to be set in your config.

### Upload to App Store Connect

```bash
uv run ksproject apple ios archive --upload \
    --asc-key-id ABC123 \
    --asc-issuer-id 00000000-0000-0000-0000-000000000000 \
    --asc-key-path ~/keys/AuthKey_ABC123.p8 \
    --build-number 42 \
    --app-version 1.2.3
```

| Flag | Env fallback | Purpose |
|------|--------------|---------|
| `--asc-key-id` | `ASC_KEY_ID` | App Store Connect API Key ID |
| `--asc-issuer-id` | `ASC_ISSUER_ID` | App Store Connect API Issuer ID |
| `--asc-key-path` | `ASC_KEY_PATH` | Path to the `.p8` API key file |
| `--build-number` | — | Stamps `CFBundleVersion` before archiving (e.g. CI run number) |
| `--app-version` | — | Stamps `CFBundleShortVersionString` (e.g. tag `1.2.3`) |

### App Store CI Workflow

```bash
uv run ksproject apple ios create-action     # or: apple macos create-action
```

Writes a **tag-triggered GitHub Actions workflow** that archives and uploads to App Store Connect. Configure these repository secrets: `APPLE_CERT_P12_BASE64`, `APPLE_CERT_PASSWORD`, `ASC_KEY_P8`, `ASC_KEY_ID`, `ASC_ISSUER_ID`.

---

## Generated Project Structure

After building, `project_dist/xcode/` contains:

```
project_dist/xcode/
├── project.yml                     # XcodeGen specification (regenerated)
├── <AppName>.xcodeproj/            # Generated Xcode project
├── Sources/
│   ├── Shared/
│   │   └── KivyLauncher.swift      # Python runtime launcher
│   ├── IphoneOS/
│   │   └── main.swift              # iOS entry point
│   └── MacOS/
│       └── main.swift              # macOS entry point
├── Resources/
│   ├── Images.xcassets/            # App icon catalog
│   └── Launch Screen.storyboard    # iOS splash screen
├── Frameworks/
│   ├── Python.xcframework/         # BeeWare's Python runtime
│   ├── SDL2.xcframework/           # From the Kivy wheel's .frameworks/
│   ├── SDL2_image.xcframework/
│   ├── SDL2_ttf.xcframework/
│   ├── SDL2_mixer.xcframework/
│   └── dylib-Info-template.plist   # Dynamic library plist template
├── site_packages/
│   ├── iphoneos/                   # Packages for physical device
│   ├── iphonesimulator/            # Packages for simulator
│   ├── macos-arm64/                # Packages for macOS (Apple Silicon)
│   └── macos-x86_64/               # Packages for macOS (Intel)
├── app/
│   └── __main__.py                 # Python entry point
├── build/                          # xcodebuild derived data + products
└── archives/                       # .xcarchive output
```

### XcodeGen Spec (project.yml)

The `project.yml` file is an [XcodeGen](https://github.com/yonaskolb/XcodeGen) specification that defines:

- **Build settings** — deployment targets (from `minimum_deployment` in your config; defaults iOS 15.6, macOS 11.5), code signing, search paths
- **Targets** — iOS and macOS platform targets
- **Build phases** — framework embedding, site-packages sync, release byte-compilation
- **Frameworks** — every `.xcframework` present in `Frameworks/`

You can open the generated `.xcodeproj` directly in Xcode for additional configuration or debugging:

```bash
uv run ksproject apple xcode open
```

### Customizing the Spec (xcode.yaml)

`project.yml` is regenerated by ksproject, so hand edits to it are overwritten. To add extra things to the project — SPM packages, framework dependencies, build settings — create an `xcode.yaml` (or `xcode.yml`) in your project root. ksproject merges it into the generated spec before running XcodeGen:

```yaml
# xcode.yaml — merged into the generated project.yml
options:
  developmentLanguage: de
targets:
  MyApp:                      # your app_name from pyproject.toml
    dependencies:
      - sdk: CoreML.framework
    settings:
      base:
        OTHER_LDFLAGS: -lz
```

Any [XcodeGen project spec](https://github.com/yonaskolb/XcodeGen/blob/master/Docs/ProjectSpec.md) key is allowed. The merge is additive — nothing generated is removed:

- **Dictionaries** merge recursively
- **Lists** are appended after the generated entries
- Only where the same scalar key exists on both sides does your value win

Changes to `xcode.yaml` are picked up on the next build, which rewrites `project.yml` and re-runs XcodeGen automatically.

---

## Framework Dependencies

| Framework | Source | Purpose |
|-----------|--------|---------|
| Python.xcframework | [BeeWare Python-Apple-support](https://github.com/beeware/Python-Apple-support) | CPython runtime for iOS/macOS (version follows your [`.python-version` pin](../configuration/pyproject-toml.md#python-version)) |
| SDL2 / SDL2_image / SDL2_ttf / SDL2_mixer | Shipped inside the Kivy wheel's [`.frameworks/`](site-packages.md) | Window management, input, OpenGL, images, fonts, audio |

Python.xcframework downloads are cached in `~/.kivyschool/apple_support/` and shared across projects. The SDL2 xcframeworks arrive automatically with the Kivy wheel during site-packages installation — see [Site-Packages & Frameworks](site-packages.md) for the mechanism.

The launcher code (`KivyLauncher.swift`) is vendored directly into `Sources/Shared/` — the only Swift Package Manager dependency is [PathKit](https://github.com/kylef/PathKit), used for path handling.

---

## Platform Slices

Apple builds handle multiple platform variants:

| Platform | Architecture | site_packages dir | Use Case |
|----------|-------------|-------------------|----------|
| `iphoneos` | arm64 | `site_packages/iphoneos` | Physical iPhone/iPad |
| `iphonesimulator` | arm64 or x86_64 (host) | `site_packages/iphonesimulator` | Simulator |
| `macos` (Apple Silicon) | arm64 | `site_packages/macos-arm64` | Native macOS app |
| `macos` (Intel) | x86_64 | `site_packages/macos-x86_64` | Native macOS app |

Each platform slice gets its own site-packages directory with appropriately cross-compiled wheels; a build phase rsyncs the right slice into the app bundle. Release builds byte-compile the synced site-packages with a uv-managed interpreter matching the bundled CPython.

---

## Troubleshooting

### "No signing certificate found"

For physical device deployment or archiving:

1. Set `developer_team = "YOURTEAMID"` in `[tool.kivy-school.ios]` (and/or `.macos`) for automatic signing, **or**
2. Open the project with `uv run ksproject apple xcode open`, select the target → "Signing & Capabilities", pick your team, and rebuild.

### Simulator Not Found

```bash
# List all available simulators
uv run ksproject apple sim devices

# Create a new simulator if needed
xcrun simctl create "iPhone 16 Pro" "com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro"
```

### Unsupported Python Version

If your `.python-version` pins a patch release BeeWare doesn't ship, the build fails immediately with the list of supported versions. Pin one of the [supported versions](../configuration/pyproject-toml.md#python-version) or remove the pin.
