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
        ).lower()

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

    def _collect_site_packages_dlls(self, site_packages_dir: Path) -> None:
        """
        Scans the newly provisioned site-packages directory for required DLLs 
        and copies them into the site-packages/libs folder.
        This ensures they are packaged into the monolithic zip and easily found by 
        the Windows DLL loader.
        """
        libs_dir = site_packages_dir / "libs"
        libs_dir.mkdir(parents=True, exist_ok=True)

        print(f"[ksproject] Scanning {site_packages_dir} for required DLLs...")
        dll_count = 0

        for dll_file in list(site_packages_dir.rglob("*.dll")):
            # Prevent copying a DLL onto itself
            if libs_dir in dll_file.parents:
                continue

            dest_file = libs_dir / dll_file.name
            if not dest_file.exists():
                shutil.copy2(dll_file, dest_file)
                print(f"  -> Collected DLL: {dll_file.name}")
                dll_count += 1

        if dll_count > 0:
            print(f"[ksproject] Collected {dll_count} native DLLs into libs directory.")

    def _inject_tkinter(self, env_dir: Path, site_packages_dir: Path) -> None:
        """Rips the Tkinter standard library and TCL runtime from the host Python and injects them."""
        import sys
        import shutil

        base_prefix = Path(sys.base_prefix)

        src_tkinter = base_prefix / "Lib" / "tkinter"
        dest_tkinter = site_packages_dir / "tkinter"
        if src_tkinter.exists() and not dest_tkinter.exists():
            print("[ksproject] Injecting Tkinter standard library...")
            shutil.copytree(src_tkinter, dest_tkinter)

        src_tcl = base_prefix / "tcl"
        dest_tcl = env_dir / "tcl"
        if src_tcl.exists() and not dest_tcl.exists():
            print("[ksproject] Injecting native TCL/TK scripts...")
            shutil.copytree(src_tcl, dest_tcl)

        dlls_dir = base_prefix / "DLLs"
        if dlls_dir.exists():
            for f in dlls_dir.glob("_tkinter.pyd"):
                shutil.copy2(f, env_dir / f.name)
            for f in dlls_dir.glob("tcl*.dll"):
                shutil.copy2(f, env_dir / f.name)
            for f in dlls_dir.glob("tk*.dll"):
                shutil.copy2(f, env_dir / f.name)
            for f in dlls_dir.glob("zlib*.dll"):
                shutil.copy2(f, env_dir / f.name)

    def generate(self, fmt: str = "standalone", variant: str = "release") -> None:
        dist_dir = self.working_dir / "project_dist" / "windows"
        dist_dir.mkdir(parents=True, exist_ok=True)

        if fmt != "payload":
            exe_path = dist_dir / f"{self.package_name}.exe"
            if exe_path.exists():
                try:
                    exe_path.unlink()
                    print(f"[ksproject] Removed old build: {exe_path.name}")
                except PermissionError:
                    print(f"\n[ksproject] ERROR: Cannot delete '{exe_path.name}'.")
                    print("[ksproject] Windows says the file is in use. Is the app still running?")
                    print("[ksproject] Please close the app and try building again.\n")
                    import sys
                    sys.exit(1)

        py_version = self.windows.python_version or "3.13.5"
        optimize = True if variant == "release" else getattr(self.windows, "byte_compile_python", False)

        env_dir = dist_dir / "windows_env"
        icon_path = self._resolve_and_convert_icon(dist_dir)

        # In the new pip --prefix installation, site-packages is inside env_dir
        site_packages_dir = env_dir / "Lib" / "site-packages"

        if site_packages_dir.exists():
            self._collect_site_packages_dlls(site_packages_dir)
            if getattr(self.windows, "include_tkinter", False):
                self._inject_tkinter(env_dir, site_packages_dir)
        
        payload_path = MsvcBuildFiles.prepare_payload(
            self.package_name,
            dist_dir,
            env_dir,
            python_version=py_version,
            optimize=optimize,
            fmt=fmt
        )

        req_admin = getattr(self.windows, "require_admin", False)

        if fmt == "payload":
            print("[ksproject] Generating metadata.toml for payload...")
            metadata_path = dist_dir / "metadata.toml"
            project_data = self.pyproject.data.get("project", {})
            authors = project_data.get("authors", [])
            author = authors[0].get("name", "") if authors else ""
            desc = project_data.get("description", "")
            version = project_data.get("version", "1.0.0")
            incl_tk = "true" if getattr(self.windows, "include_tkinter", False) else "false"
            
            metadata_content = f"""[app]
name = "{self.app_name}"
version = "{version}"
description = "{desc}"
author = "{author}"
entrypoint = "{self.package_name}"

[environment]
python_version = "{py_version}"
architecture = "amd64"
include_tkinter = {incl_tk}

[installer]
install_dir = "%PROGRAMFILES%\\\\{self.package_name}"
extract_dir = "."
create_desktop_shortcut = true
create_start_menu_shortcut = true
privacy_agreement_required = false
license_file = "LICENSE.txt"
require_admin = {"true" if req_admin else "false"}

[[installer.registry_keys]]
root = "HKLM"
key = "Software\\\\{self.package_name}"
value_name = "InstallPath"
value_type = "REG_SZ"
value_data = "{{install_dir}}"
"""
            metadata_path.write_text(metadata_content, encoding="utf-8")
        
        MsvcBuildFiles.write_main_c(dist_dir, self.package_name, py_version)
        MsvcBuildFiles.write_resources_rc(dist_dir, payload_path if fmt == "standalone" else None, icon_path, req_admin)

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
