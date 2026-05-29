# ksproject

Cross-platform build tool for **Python + Kivy** apps targeting Android and iOS.
Generates a pure AGP Gradle project, downloads the Android SDK / NDK / JDK on
demand, and builds an APK or AAR — no `buildozer`, no `python-for-android`.

📖 **[Full Documentation](https://kivy-school.github.io/ksproject/)**

---

## Quick Start

```bash
# Create project
uv init --package myapp --python 3.13
cd myapp
uv add git+https://github.com/kivy-school/ksproject --dev
uv run ksproject init

# Run on desktop
uv run myapp

# Build for Android (SDK/NDK auto-installed on first run)
uv run ksproject android build

# Install & launch on a device
uv run ksproject android run --name Pixel9
```

---

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

Everything else (Android SDK, NDK, JDK, Gradle) is downloaded automatically.

---

## Command Reference

| Command | Description |
| ------- | ----------- |
| `ksproject init` | Scaffold a new project |
| `ksproject android build [debug\|release]` | Build an APK |
| `ksproject android build --aar` | Build an AAR library |
| `ksproject android devices` | List adb devices and AVDs |
| `ksproject android run --name <AVD>` | Install and launch on an emulator |
| `ksproject android run --uuid <serial>` | Install and launch on a USB device |

---

## Documentation

For detailed guides on configuration, Android/iOS builds, services, plugins, and more:

👉 **https://kivy-school.github.io/ksproject/**
