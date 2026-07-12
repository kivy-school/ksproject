from pathlib import Path

from ksp_bootstraps.gradle.android_manifest_template import ANDROID_MANIFEST
from ksp_bootstraps.gradle.build_gradle_template import BUILD_GRADLE

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
        return ANDROID_MANIFEST
    
    def _ensure_build_gradle_template(self) -> None:
        tmpl_path = self.root / "build.tmpl.gradle.kts"
        if not tmpl_path.exists():
            tmpl_path.write_text(self.default_build_gradle_template(), encoding="utf-8")

    def default_build_gradle_template(self) -> str:
        return BUILD_GRADLE
    
    def _ensure_base_dirs(self) -> None:
        (self.root / ".java").mkdir(exist_ok=True)
        services_dir = self.root / "src" / self.module_name / "services"
        services_dir.parent.mkdir(parents=True, exist_ok=True)
        services_dir.mkdir(exist_ok=True)
        (services_dir / "__init__.py").touch()
