"""Orchestrates MSVC project generation. Ported from GradleProjectBuilder."""

from __future__ import annotations

import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

from ..pyproject_toml import PyProjectToml
from .msvc_build_files import MsvcBuildFiles


class MsvcProjectBuilder:

    def __init__(self, pyproject: PyProjectToml, working_dir: Path):
        self.pyproject = pyproject
        self.working_dir = working_dir

        kivy_school = pyproject.tool.kivy_school
        if kivy_school is None or kivy_school.windows is None:
            raise ValueError("[tool.kivy-school.windows] is missing in pyproject.toml")

        self.kivy_school = kivy_school
        self.windows = kivy_school.windows
        self.app_name = kivy_school.app_name or pyproject.project.name
        self.package_name = (
            self.pyproject.project.name.strip().replace("-", "_").replace(" ", "_")
        )

    def _resolve_and_convert_icon(self, dest_dir: Path) -> Path | None:
        """Finds the user's icon and ensures it is an .ico file for MSVC."""
        user_value: str | None = getattr(self.windows, "icon", None)

        if user_value:
            src_icon = Path(user_value)
            if not src_icon.is_absolute():
                src_icon = self.working_dir / src_icon
        else:
            templates = Path(__file__).parent.parent / "templates"
            src_icon = templates / "icon.png"

        if not src_icon.exists():
            print(f"[ksproject] Warning: Icon not found at {src_icon}")
            return None

        dest_ico = dest_dir / "icon.ico"

        if src_icon.suffix.lower() == ".ico":
            shutil.copy2(src_icon, dest_ico)
            return dest_ico

        if Image is None:
            print(
                "[ksproject] Pillow is required to convert icons to .ico. Continuing without icon."
            )
            return None

        print(f"[ksproject] Converting {src_icon.name} to Windows .ico format...")
        img = Image.open(src_icon)
        img.save(
            dest_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)]
        )
        return dest_ico

    def _copy_venv_dlls(self, site_packages_dir: Path) -> None:
        """
        Scans the active virtual environment (.venv) created by uv
        and copies required DLLs (like Kivy's SDL2/GLEW) into the
        site-packages/libs folder so they get packaged into the monolithic zip.
        """
        venv_dir = self.working_dir / ".venv"
        share_dir = venv_dir / "share"

        if not share_dir.exists():
            return

        libs_dir = site_packages_dir / "libs"
        libs_dir.mkdir(parents=True, exist_ok=True)

        print(f"[ksproject] Scanning {share_dir} for required DLLs...")
        dll_count = 0

        for dll_file in share_dir.rglob("*.dll"):
            dest_file = libs_dir / dll_file.name

            if not dest_file.exists():
                shutil.copy2(dll_file, dest_file)
                print(f"  -> Copied: {dll_file.name}")
                dll_count += 1

        if dll_count > 0:
            print(f"[ksproject] Zipping {dll_count} native DLLs into payload...")

    def generate(self, variant: str = "release") -> None:
        dist_dir = self.working_dir / "project_dist" / "windows"
        dist_dir.mkdir(parents=True, exist_ok=True)

        py_version = self.windows.python_version or "3.11.5"
        optimize = True if variant == "release" else self.windows.byte_compile_python

        env_dir = MsvcBuildFiles.provision_embeddable_python(dist_dir, py_version)
        icon_path = self._resolve_and_convert_icon(dist_dir)

        site_packages_dir = (
            self.working_dir / "project_dist" / "windows" / "site_packages" / "windows"
        )

        self._copy_venv_dlls(site_packages_dir)

        payload_path = MsvcBuildFiles.create_payload_zip(
            self.package_name,
            dist_dir,
            site_packages_dir,
            env_dir,
            python_version=py_version,
            optimize=optimize,
        )

        req_admin = self.windows.require_admin

        MsvcBuildFiles.write_main_c(dist_dir, self.package_name, py_version)
        MsvcBuildFiles.write_resources_rc(dist_dir, payload_path, icon_path, req_admin)

        if self.windows and hasattr(self.windows, "include_files"):
            for dest_str, sources in self.windows.include_files:
                target_dir = dist_dir / dest_str
                target_dir.mkdir(parents=True, exist_ok=True)

                for src_str in sources:
                    src_path = self.working_dir / src_str
                    if src_path.is_dir():
                        shutil.copytree(
                            src_path, target_dir / src_path.name, dirs_exist_ok=True
                        )
                    elif src_path.exists():
                        shutil.copy2(src_path, target_dir / src_path.name)
