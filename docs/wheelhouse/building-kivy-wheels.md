# Building Kivy Wheels

ksproject's default bootstraps target **Kivy 2.3.x** and **Kivy 3.0.0**. Pre-built wheels are published on the KivySchool indexes — but you don't have to wait for them. Both source trees build with [cibuildwheel](https://cibuildwheel.pypa.io/), so you can produce the exact platform wheels you need yourself, then drop them into your app's [wheelhouse](overview.md).

Typical reasons to do this:

- You patched Kivy and want your fork on device
- You want to track Kivy master ahead of published wheels
- You need an arch or platform combination that isn't published yet

---

## Prerequisites

Install cibuildwheel (3.2 or newer — the first release supporting both iOS and Android targets):

```bash
uv tool install cibuildwheel
```

What you can build depends on your host machine:

| Target | Host requirement |
|--------|------------------|
| iOS | macOS with Xcode |
| Android | Linux or macOS, with an Android NDK |
| macOS | macOS with Xcode command line tools |
| Linux | Linux (or any host with Docker) |
| Windows | Windows |

!!! tip "Build only the Python version you ship"
    ksproject bundles CPython 3.13. Restrict cibuildwheel to it and skip the rest:

    ```bash
    export CIBW_BUILD="cp313-*"
    ```

---

## Kivy 2.3.x (`kivy2x`)

[kivy-school/kivy2x](https://github.com/kivy-school/kivy2x) is the maintained Kivy 2.3.x tree with cibuildwheel configuration baked in — no extra environment setup beyond the Android NDK.

```bash
git clone https://github.com/kivy-school/kivy2x
cd kivy2x
```

=== "iOS"

    ```bash
    cibuildwheel --platform ios --archs all --output-dir ./wheelhouse
    ```

    `--archs all` builds device (`arm64_iphoneos`) and simulator (`arm64_iphonesimulator`, `x86_64_iphonesimulator`) wheels.

=== "Android"

    Point `ANDROID_NDK_HOME` at an NDK — if you've already built with ksproject, the one it installed works:

    ```bash
    export ANDROID_NDK_HOME="$HOME/.kivyschool/android-sdk/ndk/28.2.13676358"
    cibuildwheel --platform android --archs all --output-dir ./wheelhouse
    ```

    `--archs all` builds `arm64_v8a` and `x86_64` wheels.

=== "macOS"

    ```bash
    cibuildwheel --platform macos --archs all --output-dir ./wheelhouse
    ```

    (`--platform` can be omitted on a macOS host — it defaults to the host platform.)

=== "Linux"

    ```bash
    cibuildwheel --platform linux --archs all --output-dir ./wheelhouse
    ```

    (`--platform` can be omitted on a Linux host.)

=== "Windows"

    ```powershell
    cibuildwheel --platform windows --archs all --output-dir ./wheelhouse
    ```

    (`--platform` can be omitted on a Windows host.)

The wheels land in `./wheelhouse` inside the clone — copy them into your app afterwards (see [Using the wheels](#using-the-wheels-in-your-app)).

---

## Kivy 3.0.0 (master)

Kivy 3.0.0 builds from the official [kivy/kivy](https://github.com/kivy/kivy) master branch. Unlike kivy2x, its native dependencies (SDL3 and friends) must be compiled first — the repo ships `tools/build_*_dependencies.sh` scripts for this, which you hook into cibuildwheel via `CIBW_BEFORE_ALL_*`.

```bash
git clone https://github.com/kivy/kivy
cd kivy
```

=== "iOS"

    ```bash
    export KIVY_DEPS_ROOT=$(pwd)/ios-kivy-dependencies
    export CIBW_BEFORE_ALL_IOS=./tools/build_ios_dependencies.sh
    cibuildwheel --platform ios --archs all --output-dir ./wheelhouse
    uv run ./tools/add-ios-frameworks.py ./wheelhouse
    ```

    The final step embeds the dependency xcframeworks into the wheels — don't skip it, the wheels won't link on device without it.

=== "Android"

    !!! warning "Work in progress"
        Android wheels for Kivy 3.0.0 are not buildable out-of-the-box yet. The remaining pieces:

        - A `build_android_dependencies.sh` before-all script (doesn't exist upstream yet)
        - Packaging of the ThorVG dependency for Android
        - A post-build step to bundle SDL3 / ThorVG shared libraries into the wheel's `.libs/` so they end up merged into `site-packages/.libs`

        Once those land, the build will look like:

        ```bash
        export ANDROID_NDK_HOME="$HOME/.kivyschool/android-sdk/ndk/28.2.13676358"
        export CIBW_BEFORE_ALL_ANDROID="./tools/build_android_dependencies.sh"
        cibuildwheel --platform android --archs all --output-dir ./wheelhouse
        ```

        Until then, use **kivy2x** for Android.

=== "macOS"

    ```bash
    export CIBW_BEFORE_ALL_MACOS="./tools/build_macos_dependencies.sh"
    cibuildwheel --platform macos --archs all --output-dir ./wheelhouse
    ```

=== "Linux"

    ```bash
    export CIBW_BEFORE_ALL_LINUX="./tools/build_linux_dependencies.sh"
    cibuildwheel --platform linux --archs all --output-dir ./wheelhouse
    ```

---

## Using the Wheels in Your App

Copy the built wheels into your ksproject app's wheelhouse:

```bash
cp ./wheelhouse/*.whl /path/to/myapp/wheelhouse/
```

Then make sure your dependency constraint matches what you built:

=== "Kivy 2.3.x"

    The default constraint already covers it:

    ```toml
    dependencies = [
        "kivy>=2.3.1,<3.0.0",
    ]
    ```

=== "Kivy 3.0.0"

    Master builds a pre-release version, so pin it exactly (an exact pin opts in to pre-releases):

    ```toml
    dependencies = [
        "kivy==3.0.0.dev0",
    ]
    ```

Build as usual — uv resolves the wheelhouse via `find-links` and installs your wheels into the cross-compiled site-packages:

```bash
uv run ksproject android build
# or
uv run ksproject apple build
```

!!! tip "Verify which wheel was picked"
    The `uv pip install` output during the build lists the resolved distributions. A wheel installed from the wheelhouse shows a `file://` path instead of an index URL.
