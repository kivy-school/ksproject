# ksproject

**Kivy School Project Manager** — A cross-platform build tool for Kivy apps targeting Android (iOS/macOS, windows and linux soon).

`ksproject` generates a pure AGP (Android Gradle Plugin) Gradle project, downloads the Android SDK, NDK, and JDK completely on demand, and builds your APK, AAB, or AAR.

No `buildozer`, no `python-for-android` at build time — just a clean, native Gradle project under `project_dist/gradle/` that you can open and debug directly in Android Studio.

---

## Requirements

* Python 3.13
* [uv](https://docs.astral.sh/uv/) (used for environment and dependency management)

Everything else (Android SDK, NDK, JDK, Gradle wrapper) is downloaded automatically on the first build into `.kivyschool/` inside your project directory or globally.

---

## 1. Create a New Project

```bash
uv init --package hello-world --python 3.13
cd hello-world
uv add git+https://github.com/kivy-school/ksproject@master --dev
uv run ksproject init

```

`ksproject init` handles the heavy lifting of project scaffolding. It:

* Writes a starter `main.py` and `app.kv` in `src/hello_world/`.
* Creates a `src/hello_world/services/` directory (with an `__init__.py`) for Android background services.
* Adds a comprehensive `[tool.kivy-school]` block to your `pyproject.toml`.
* Generates **`AndroidManifest.tmpl.xml`** and **`build.tmpl.gradle.kts`** in your project root so you can customize native build behaviors directly.
* Creates a `.java` folder for native code injections.

## 2. Add Kivy

```bash
uv add kivy

```

## 3. Add Platform-Specific Dependencies

`pyjnius` is only meaningful on Android. Mark it with a PEP 508 marker so `uv` won't try to install it on macOS, Linux, or Windows:

> [!NOTE]
> These are already present by default!!

```bash
uv add "pyjnius ; sys_platform == 'android'"

```

Same trick for iOS (coming soon):

```bash
uv add "pyobjus ; sys_platform == 'ios'"

```

Optional scientific stack:

```bash
uv add numpy matplotlib

```

## 4. Run on Desktop

```bash
uv run hello-world

```

This launches the entry point declared in `pyproject.toml` — the exact same code that will run on Android, with no changes needed.

---

## 5. Build for Android

```bash
uv run ksproject android build

```

The first run downloads the required toolchain:

* Android command-line tools + SDK (API `36`, build-tools)
* NDK `28c` (or your configured version)
* Temurin JDK 21 (via `sdkman`)
* Gradle 9.5.0 wrapper
* CPython-for-Android prebuilt wheels

The output APK lands at:
`project_dist/gradle/app/build/outputs/apk/debug/app-debug.apk`

### Release Builds & Formats

```bash
# Build a Release APK
uv run ksproject android build release

# Build an Android App Bundle (.aab) for Google Play
uv run ksproject android build release --bundle

# Build an AAR (library) instead of an app
uv run ksproject android build release --aar

```

---

## 6. Run on an Emulator

List attached devices and available AVDs:

```bash
uv run ksproject android devices

```

*Example output:*

```text
avd     name=Pixel9
device  serial=emulator-5554     state=device       model=sdk_gphone64_arm64

```

Boot an AVD by name (boots it, builds the app, installs it, and launches):

```bash
uv run ksproject android run --name Pixel9

```

## 7. Run on a Real Device

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

*(Append `--variant release` to run the production build instead of debug).*

---

## 8. App Signing & Keystore Generation

ksproject includes built-in tools for generating secure keystores and signing your production artifacts (.apk and .aab) using standard Android SDK/JDK tools.

### 💡 Pro-Tip: Streamline with a .env File
To keep your passwords out of your terminal history and to make commands significantly shorter, save your credentials in a .env file at the root of your project. ksproject will automatically detect them.
Create a .env file and add your variables like this:

```env
# .env

# App Signing Credentials
KSPROJECT_KEYSTORE="my-release-key.jks"
KSPROJECT_KEYALIAS="myapp"
KSPROJECT_STOREPASS="SecretPass123"
# KSPROJECT_KEYPASS="defaults_to_storepass"
```

### 1. Generate a Release Keystore
This is required only when your key is outdated or you need to generate a new key for the first time.

**Using explicit flags:**
```bash
uv run ksproject android genkey --out my-release-key.jks --storepass SecretPass123 --keyalias myapp
```

**Using your .env file:**
```bash
uv run ksproject android genkey --dname "CN=My App, O=My Org"

```
> [!NOTE]
> You can also append --dname "CN=My App, O=My Org" to either command if you need to provide a specific Distinguished Name string for the certificate.

### 2. Sign a Built Artifact
The orchestrator automatically detects your built release binary and signs it.
**Using explicit flags:**

```bash
# Sign the APK
uv run ksproject android sign --keystore my-release-key.jks --storepass SecretPass123 --keyalias myapp

# Sign an App Bundle (.aab)
uv run ksproject android sign --bundle --keystore my-release-key.jks --storepass SecretPass123 --keyalias myapp
```

**Using your .env file:**
```bash
# Sign the APK
uv run ksproject android sign

# Sign an App Bundle (.aab)
uv run ksproject android sign --bundle

```

> [!NOTE]
> By default, `ksproject android sign` targets the `release` directory. You can optionally pass `--variant debug` to sign a debug artifact, or pass `--keypass <password>` if your security profile requires an alias password distinct from your core keystore storage password. Similarly, you can append `--variant release` to the `run` pipeline to run production builds.

---

## 9. Advanced Customization (Templates)

When you run `init`, `ksproject` creates two highly important template files in your root directory. The build engine uses these to generate the final `project_dist/` payload.

* **`AndroidManifest.tmpl.xml`**: Add custom broadcast receivers, specific hardware features, or specific intent filters here. `ksproject` will automatically inject your Python services, meta-data, and permissions at build time.
* **`build.tmpl.gradle.kts`**: Modify your core Gradle setup. Need custom Maven repositories or `externalNativeBuild` flags? Put them here.
* *Note on Push Notifications:* The default template automatically maps the system environment variable `ONESIGNAL_APP_ID` to an Android String Resource (`onesignal_app_id`), making it instantly available for libraries like `pyonesignal`.



---

## 10. Configuration (`pyproject.toml`)

Your `pyproject.toml` is the single source of truth for your app's metadata.

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

#### kivy-school configuration ####

[tool.kivy-school]
app_name = "Hello World"

[tool.kivy-school.android]
package_name = "org.example.hello_world"
archs = [
    "arm64-v8a", 
    # "x86_64" # Uncomment to support emulators (increases APK size)
]

# API and Toolchain Versions
api = 36
min_api = 24
sdk = "36"
ndk = "28c"
ndk_api = 24

# --- Toolchain Management ---
global_tools = true  # Set to false to use project-local SDK/NDK (./.kivyschool)
# global_tools_path = "~/.kivyschool" # Override root path when global_tools = true

# --- Gradle & Manifest Configs ---
gradle_dependencies = [
    # "com.onesignal:OneSignal:[5.6.1, 5.9.99]"
]
gradle_plugins = [
    # 'id("com.google.gms.google-services") version "4.4.2" apply false'
]
permissions = [
    # "POST_NOTIFICATIONS", "INTERNET", "ACCESS_NETWORK_STATE"
]

# <meta-data> entries inside <application>
# [tool.kivy-school.android.meta_data]
# "com.google.android.gms.ads.APPLICATION_ID" = "ca-app-pub-xxxxxxxx~xxxxxxxx"

# --- File Inclusions ---
# Format: [Destination, Source(s)]
# include_files = [
#     ["gradle/app", ["./google-services.json", "./some-other-config.xml"]]
# ]

# --- Background Services ---
# [[tool.kivy-school.android.services]]
# name = "MyService1"
# start_type = "START_NOT_STICKY"
# entrypoint = "hello_world.services.myservice1"
# foreground = true
# foreground_service_type = "location|dataSync"
# notification_title = "MyService1 Running"
# notification_text = "Service is managing background data."
# notification_icon = "stat_notify_sync"

#### iOS Configuration (Coming Soon) ####
[tool.kivy-school.ios]
bundle_id = "org.example.hello_world"
info_plist = {}
entitlements = {}
permissions = []
frameworks = []
# developer_team = "ABC123XYZ" 

```

---

## Command Reference

| Command | What it does |
| --- | --- |
| `ksproject init` | Scaffold a new project, template files, and `pyproject.toml` configurations |
| `ksproject android build [debug\release]` | Build an APK artifact |
| `ksproject android build --aar [debug\release]` | Build an AAR library instead of an APK |
| `ksproject android build --bundle [debug\release]` | Build an AAB (Android App Bundle) instead of an APK |
| `ksproject android build [debug\release] --clean` | Perform a clean step before executing the build task |
| `ksproject android sign --keystore <file> --storepass <pass> --keyalias <alias>` | Sign the built APK inside the target directory using `apksigner` |
| `ksproject android sign --bundle --keystore <file> --storepass <pass> --keyalias <alias>` | Sign the built App Bundle (.aab) inside the target directory using `jarsigner` |
| `ksproject android genkey --out <file> --storepass <pass> --keyalias <alias>` | Generate a secure Java Keystore (`.jks`) using `keytool` |
| `ksproject android get-path [sdk\ndk\emulator]` | Print the fully resolved local file system path for the specified tool |
| `ksproject android devices` | List connected active `adb` serial devices and available AVD profiles |
| `ksproject android run --name <AVD>` | Build, install, and launch the target application on a simulated emulator |
| `ksproject android run --uuid <serial>` | Build, install, and launch the target application on a physical USB device |
