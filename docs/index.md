---
hide:
  - navigation
  - toc
---

<div class="hero-section" markdown>

# ksproject

<p class="hero-tagline">
Compile <strong>Python + Kivy</strong> apps for Android and iOS — toolchain setup, native builds, and dependency management in a single CLI.
</p>

[:material-rocket-launch: New Project](getting-started/new-project.md){ .md-button .md-button--primary }
[:material-cog: Configuration](configuration/pyproject-toml.md){ .md-button }
[:fontawesome-brands-github: GitHub](https://github.com/kivy-school/ksproject){ .md-button }

<div class="hero-stats" markdown>
<div class="stat" markdown>
<span class="stat-value">Android + iOS</span>
<span class="stat-label">Native Builds</span>
</div>
<div class="stat" markdown>
<span class="stat-value">UV Powered</span>
<span class="stat-label">Python Toolchain</span>
</div>
<div class="stat" markdown>
<span class="stat-value">Extensible</span>
<span class="stat-label">Plugin Ecosystem</span>
</div>
</div>

</div>

<div class="section-header" markdown>

## :material-lightning-bolt: Why ksproject?

One tool to go from Python code to native mobile apps — no manual Gradle or Xcode setup.

</div>

<div class="grid cards" markdown>

-   :material-plus-circle:{ .lg .middle } **Instant Project Setup**

    ---

    `uv run ksproject init` creates a complete project with Kivy app template, pyproject.toml config, and all the scaffolding for mobile builds — ready in seconds.

    [:octicons-arrow-right-24: Create a project](getting-started/new-project.md)

-   :fontawesome-brands-android:{ .lg .middle } **Android Builds**

    ---

    Automatic SDK/NDK/Java installation, Gradle project generation, multi-arch APK/AAB builds, keystore signing, and one-command deploy to emulators or physical devices.

    [:octicons-arrow-right-24: Build for Android](android/building.md)

-   :fontawesome-brands-apple:{ .lg .middle } **iOS & macOS Builds**

    ---

    XcodeGen-based project generation with Python.xcframework, SDL2, App Store archiving, and one-command deploy to simulators or devices via xcodebuild.

    [:octicons-arrow-right-24: Build for iOS](ios/building.md)

-   :material-package-variant:{ .lg .middle } **Plugin Ecosystem**

    ---

    Install pip packages that automatically inject Java sources, Gradle dependencies, Android permissions, and iOS frameworks into your app at build time.

    [:octicons-arrow-right-24: Explore plugins](plugins/overview.md)

-   :material-wrench:{ .lg .middle } **Automatic Toolchain**

    ---

    ksproject downloads and manages Android SDK, NDK, Java (via sdkman), build tools, and system images — no manual setup required.

    [:octicons-arrow-right-24: Configuration](configuration/pyproject-toml.md)

-   :material-file-document:{ .lg .middle } **pyproject.toml Driven**

    ---

    All configuration lives in a single `pyproject.toml` under `[tool.kivy-school]` — package name, permissions, services, build variants, and more.

    [:octicons-arrow-right-24: Full reference](configuration/pyproject-toml.md)

</div>

---

<div class="section-header" markdown>

## :material-code-tags: Quick Start

From zero to running on your phone in three commands.

</div>

```bash
# 1. Create a new project
uv init --package myapp --python 3.13
cd myapp
uv add git+https://github.com/kivy-school/ksproject --dev
uv run ksproject init

# 2. Build for Android (SDK/NDK auto-installed on first run)
uv run ksproject android build

# 3. Run on a connected device
uv run ksproject android run --name "Pixel_8"
```

---

<div class="section-header" markdown>

## :material-view-grid: How It Works

</div>

<div class="grid cards" markdown>

-   :material-numeric-1-circle:{ .lg .middle } **Initialize**

    ---

    `uv run ksproject init` scaffolds a UV-managed Python project with Kivy app sources, a `pyproject.toml` containing `[tool.kivy-school]` config, and platform templates.

-   :material-numeric-2-circle:{ .lg .middle } **Configure**

    ---

    Define your app name, package ID, permissions, services, and dependencies in `pyproject.toml`. ksproject reads everything from there — no external config files.

-   :material-numeric-3-circle:{ .lg .middle } **Build**

    ---

    `uv run ksproject android build` or `uv run ksproject apple ios build` generates native project files, installs cross-compiled site-packages per architecture, and compiles the final app.

-   :material-numeric-4-circle:{ .lg .middle } **Run**

    ---

    Deploy directly to emulators, simulators, or physical devices. ksproject handles ADB, simctl, and devicectl for you.

</div>

---

<div class="section-header" markdown>

## :material-compass: Explore the Documentation

</div>

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **New Project**

    ---

    Create a complete Kivy project with all the scaffolding for Android and iOS builds in one command.

    [:octicons-arrow-right-24: Get started](getting-started/new-project.md)

-   :material-cog:{ .lg .middle } **pyproject.toml Reference**

    ---

    Complete reference for every configuration key — Android package names, iOS bundle IDs, permissions, services, and build settings.

    [:octicons-arrow-right-24: Configuration](configuration/pyproject-toml.md)

-   :fontawesome-brands-android:{ .lg .middle } **Android Guide**

    ---

    Build APKs, AABs, and AARs. Deploy to emulators and devices. Understand how site-packages, Java, and Gradle configs are merged.

    [:octicons-arrow-right-24: Android docs](android/building.md)

-   :fontawesome-brands-apple:{ .lg .middle } **iOS Guide**

    ---

    Build for simulators and devices. Understand how xcframeworks and site-packages work in the Xcode project.

    [:octicons-arrow-right-24: iOS docs](ios/building.md)

-   :material-puzzle:{ .lg .middle } **Plugin Development**

    ---

    Create pip packages that inject Java sources, Gradle dependencies, and permissions into apps that install them.

    [:octicons-arrow-right-24: Plugin guide](plugins/overview.md)

-   :material-package-down:{ .lg .middle } **Wheelhouse**

    ---

    Drop your own platform wheels — a patched Kivy, an unreleased dependency — into `wheelhouse/` and ksproject uses them in mobile builds.

    [:octicons-arrow-right-24: Wheelhouse guide](wheelhouse/overview.md)

</div>
