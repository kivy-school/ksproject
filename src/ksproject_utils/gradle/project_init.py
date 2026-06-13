from pathlib import Path


class GradleProjectInit:

    root: Path
    module_name: str

    def __init__(self, root: Path, module_name: str):
        self.root = root
        self.module_name = module_name

    # files to write

    def execute(self) -> None:
        self._ensure_android_manifest()
        self._ensure_build_gradle_template()
        self._ensure_base_dirs()

    ########################################################################

    def _ensure_android_manifest(self) -> None:
        tmpl_path = self.root / "AndroidManifest.tmpl.xml"
        if not tmpl_path.exists():
            tmpl_path.write_text(
                self.default_android_manifest_template(), encoding="utf-8"
            )

    def default_android_manifest_template(self) -> str:
        return """\
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

{{ permissions }}

    <application
        android:label="{{ app_name }}"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="true"
        android:supportsRtl="true"
        android:hardwareAccelerated="true"
        android:theme="@android:style/Theme.DeviceDefault.NoActionBar">{{ meta_data }}
{{ services }}
        <activity
            android:name=".MainActivity"
            android:label="{{ app_name }}"
            android:configChanges="mcc|mnc|locale|touchscreen|keyboard|keyboardHidden|navigation|orientation|screenLayout|fontScale|uiMode|screenSize|smallestScreenSize|layoutDirection|density|colorMode|fontWeightAdjustment|grammaticalGender"
            android:theme="@android:style/Theme.DeviceDefault.NoActionBar"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

    def _ensure_build_gradle_template(self) -> None:
        tmpl_path = self.root / "build.tmpl.gradle.kts"
        if not tmpl_path.exists():
            tmpl_path.write_text(self.default_build_gradle_template(), encoding="utf-8")

    def default_build_gradle_template(self) -> str:
        return """\
plugins {
    id("{{ plugin_id }}")
}

android {
    namespace = "{{ package_name }}"
    compileSdk = {{ compile_sdk }}
{{ ndk_line }}    ndkPath = "{{ ndk_path }}"

    defaultConfig {
{{ app_id_lines }}        minSdk = {{ min_sdk }}
        targetSdk = {{ target_sdk }}

        ndk {
            abiFilters += setOf({{ abi_filters }})
        }

        externalNativeBuild {
            cmake {
                arguments += listOf("-DANDROID_STL=c++_static")
            }
        }

        // ONESIGNAL_APP_ID setup for pyonesignal (reads from env and creates a string resource)
        val oneSignalId = System.getenv("ONESIGNAL_APP_ID") ?: ""
        resValue("string", "onesignal_app_id", oneSignalId)
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    // CPython stdlib and packages contain underscore-prefixed directories
    // (e.g. zipfile/_path) that AGP's default aapt ignore pattern strips.
    // Override to keep them.
    androidResources {
        ignoreAssetsPatterns.clear()
        ignoreAssetsPatterns.addAll(listOf(
            "!.svn", "!.git", "!.ds_store", "!*.scc",
            "!CVS", "!thumbs.db", "!picasa.ini", "!*~"
        ))
    }
}

dependencies {
    implementation(fileTree("libs") { include("*.aar", "*.jar") })
{{ extra_deps }}}

{{ site_packages_tasks }}
"""

    def _ensure_base_dirs(self) -> None:
        (self.root / ".java").mkdir(exist_ok=True)
        services_dir = self.root / "src" / self.module_name / "services"
        services_dir.parent.mkdir(parents=True, exist_ok=True)
        services_dir.mkdir(exist_ok=True)
        (services_dir / "__init__.py").touch()
