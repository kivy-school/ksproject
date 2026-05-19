
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

        self._ensure_base_dirs()

    ########################################################################

    def _ensure_android_manifest(self) -> None:
        tmpl_path = self.root / "AndroidManifest.tmpl.xml"
        if not tmpl_path.exists():
            tmpl_path.write_text(self.default_android_manifest_template(), encoding="utf-8")

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
            android:configChanges="orientation|screenSize|keyboardHidden"
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
            
    def _ensure_base_dirs(self) -> None:
        (self.root / ".java").mkdir(exist_ok=True)
        services_dir = self.root / "src" / self.module_name / "services"
        services_dir.mkdir(exist_ok=True)
        (services_dir / "__init__.py").touch()