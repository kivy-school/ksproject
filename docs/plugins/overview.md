# Expanding Apps with Pip Plugins

ksproject features a plugin ecosystem where **pip packages can inject native assets** — Java sources, Gradle dependencies, Android permissions, and iOS frameworks — into apps that install them. This is powered by two custom PEP 517 build backends: **ksp-builder** and **pyjnius-builder**.

---

## The Problem

You're building a Kivy app that uses Firebase. Normally you'd need to:

1. Manually add `com.google.firebase:firebase-analytics:21.0.0` to your Gradle dependencies
2. Manually add `INTERNET` and `WAKE_LOCK` permissions to your manifest
3. Manually copy Java bridge classes into your project

With ksproject plugins, the Firebase package declares all of this — and `pip install kivy-firebase` handles everything.

---

## How It Works

```
┌────────────────────────────┐
│  pip install my-plugin     │
│  (uses ksp-builder)        │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│  Wheel contains:           │
│  • .java/  (Java sources)  │
│  • .gradle/pkg.json        │
│  • Python code             │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│  ksproject android build   │
│  • Finds .java/ → compile  │
│  • Finds .gradle/ → merge  │
│  • Site-packages → assets  │
└────────────────────────────┘
```

---

## ksp-builder

[**ksp-builder**](https://github.com/kivy-school/ksp-builder) is the unified PEP 517 build backend for ksproject-based plugins. It wraps setuptools and combines three optional injection steps into a single backend.

### Setup

To create a plugin package, use `ksp-builder` as your build backend:

```toml
[build-system]
requires = ["ksp-builder"]
build-backend = "ksp_builder"
```

### What ksp-builder Provides

| Feature | Configuration Section | Injected Into Wheel |
|---------|----------------------|---------------------|
| Java sources | `[tool.pyjnius]` | `.java/` directory |
| Gradle config | `[tool.kivy-school.android]` | `.gradle/<pkg>.json` |
| Swift artifacts | `[tool.pyswiftkit]` | Compiled `.so`/`.dylib` |

---

## Injecting Java Sources

Java source files are injected following the [pyjnius-builder](https://github.com/kivy-school/pyjnius-builder) convention.

### Configuration

```toml
[tool.pyjnius]
java-paths = ["java/"]
```

### Directory Structure

```
my-plugin/
├── pyproject.toml
├── java/
│   └── org/
│       └── example/
│           └── MyBridge.java      # Custom Java code
└── my_plugin/
    └── __init__.py                # Python interface
```

### What Happens at Build Time

When `pip install` builds the wheel, ksp-builder:

1. Reads `java-paths` from `[tool.pyjnius]`
2. Collects all files from those directories
3. Injects them under `.java/` in the wheel

```
my_plugin-1.0.0-py3-none-any.whl
├── my_plugin/
│   └── __init__.py
└── .java/
    └── org/
        └── example/
            └── MyBridge.java
```

When a ksproject app installs this package and builds for Android:

1. `.java/` files land in `site_packages/.java/`
2. ksproject copies them to `app/src/main/java/`
3. Gradle compiles them with the app

---

## Injecting Gradle Dependencies & Permissions

### Configuration

```toml
[tool.kivy-school]
app_name = "MyPlugin"

[tool.kivy-school.android]
package_name = "org.example.myplugin"
gradle_dependencies = [
    "com.google.firebase:firebase-analytics:21.0.0",
    "com.google.firebase:firebase-messaging:23.0.0",
]
permissions = [
    "INTERNET",
    "WAKE_LOCK",
]
```

### What Happens at Build Time

ksp-builder generates a `.gradle/org.example.myplugin.json`:

```json
{
    "package_name": "org.example.myplugin",
    "gradle_dependencies": [
        "com.google.firebase:firebase-analytics:21.0.0",
        "com.google.firebase:firebase-messaging:23.0.0"
    ],
    "permissions": [
        "INTERNET",
        "WAKE_LOCK"
    ]
}
```

This JSON is injected into the wheel under `.gradle/`.

When a ksproject app builds:

1. All `.gradle/*.json` files from installed packages are discovered
2. Dependencies and permissions are **merged** (with deduplication)
3. Combined with the app's own `gradle_dependencies` and `permissions`
4. Written into the generated `app/build.gradle.kts` and `AndroidManifest.xml`

---

## Injecting Swift Artifacts (Optional)

If your plugin includes Swift code for iOS/macOS:

```toml
[tool.pyswiftkit]
products = ["mymodule"]
```

When `pyswiftkit_builder` is installed, ksp-builder will:

1. Run `swift build` to compile native code
2. Inject the compiled `.so`/`.dylib` into the wheel
3. Mark the wheel as platform-specific (binary distribution)

---

## pyjnius-builder (Standalone)

[**pyjnius-builder**](https://github.com/kivy-school/pyjnius-builder) is a lighter-weight alternative that **only** handles Java source injection. Use it when you don't need Gradle config or Swift support.

### Setup

```toml
[build-system]
requires = ["pyjnius-builder"]
build-backend = "pyjnius_builder"
```

### Configuration

```toml
[tool.pyjnius]
java-paths = ["src/java"]
```

pyjnius-builder wraps Hatchling and injects `.java/` files into both wheels and sdists.

---

## Complete Plugin Example

Here's a complete example of a plugin that provides Firebase Push Notifications:

### Project Structure

```
kivy-firebase-push/
├── pyproject.toml
├── java/
│   └── org/
│       └── kivyschool/
│           └── firebase/
│               └── PushService.java
└── kivy_firebase_push/
    ├── __init__.py
    └── notifications.py
```

### pyproject.toml

```toml
[build-system]
requires = ["ksp-builder"]
build-backend = "ksp_builder"

[project]
name = "kivy-firebase-push"
version = "1.0.0"
description = "Firebase push notifications for Kivy apps"
requires-python = ">=3.13"
dependencies = []

[tool.setuptools]
packages = ["kivy_firebase_push"]

[tool.pyjnius]
java-paths = ["java/"]

[tool.kivy-school]
app_name = "FirebasePush"

[tool.kivy-school.android]
package_name = "org.kivyschool.firebase.push"
gradle_dependencies = [
    "com.google.firebase:firebase-messaging:23.4.0",
    "com.google.firebase:firebase-analytics:21.5.0",
]
permissions = [
    "INTERNET",
    "WAKE_LOCK",
    "RECEIVE_BOOT_COMPLETED",
    "POST_NOTIFICATIONS",
]
```

### Java Source (java/org/kivyschool/firebase/PushService.java)

```java
package org.kivyschool.firebase;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

public class PushService extends FirebaseMessagingService {
    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        // Forward to Python via JNI bridge
    }

    @Override
    public void onNewToken(String token) {
        // Handle token refresh
    }
}
```

### Python Interface (kivy_firebase_push/notifications.py)

```python
"""Cross-platform push notification interface."""

def get_token() -> str:
    """Get the FCM registration token."""
    from jnius import autoclass
    FirebaseMessaging = autoclass("com.google.firebase.messaging.FirebaseMessaging")
    instance = FirebaseMessaging.getInstance()
    task = instance.getToken()
    # ... handle async task
    return task.getResult()
```

---

## Using a Plugin in Your App

From the app developer's perspective, it's just `pip install`:

```toml
[project]
dependencies = [
    "kivy>=2.3.1,<3.0.0",
    "kivy-firebase-push>=1.0.0",  # ← Plugin
]
```

Then build normally:

```bash
uv run ksproject android build
```

ksproject automatically:

- ✅ Installs `kivy-firebase-push` into cross-compiled site-packages
- ✅ Discovers `.java/org/kivyschool/firebase/PushService.java`
- ✅ Copies Java files into the Gradle project
- ✅ Discovers `.gradle/org.kivyschool.firebase.push.json`
- ✅ Merges Firebase Gradle dependencies into `build.gradle.kts`
- ✅ Merges permissions into `AndroidManifest.xml`
- ✅ Compiles everything into the final APK

---

## The Build Backend Stack

```
┌─────────────────────────────────────┐
│         ksp-builder                 │  ← Unified backend
│  (wraps setuptools + extensions)    │
├─────────────────────────────────────┤
│                                     │
│  ┌───────────────┐ ┌─────────────┐ │
│  │ pyjnius-builder│ │pyswiftkit-  │ │
│  │ (Java inject) │ │builder      │ │
│  │               │ │(Swift build)│ │
│  └───────────────┘ └─────────────┘ │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ _gradle.py                    │  │
│  │ (Gradle JSON inject)          │  │
│  └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         ksproject                   │  ← Build orchestrator
│  • Discovers .java/ .gradle/ .libs/ │
│  • Merges configs                   │
│  • Generates native projects        │
│  • Runs Gradle / xcodebuild         │
└─────────────────────────────────────┘
```

---

## Summary

| Backend | Use Case | Injects |
|---------|----------|---------|
| **ksp-builder** | Full-featured plugins (Java + Gradle + Swift) | `.java/`, `.gradle/*.json`, compiled Swift |
| **pyjnius-builder** | Java-only plugins | `.java/` only |

| Convention | Platform | Purpose |
|------------|----------|---------|
| `.java/` | Android | Java source files compiled into APK |
| `.gradle/*.json` | Android | Gradle dependencies + permissions |
| `.libs/<abi>/` | Android | Pre-compiled native `.so` libraries |
| `.frameworks/` | iOS/macOS | xcframeworks linked into `.app` |

The plugin system means the Python packaging ecosystem (`pip install`) becomes the delivery mechanism for native mobile assets — no manual Gradle or Xcode configuration needed.
