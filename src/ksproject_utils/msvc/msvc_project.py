"""High-level Windows MSVC project orchestrator.

Single entrypoint used by both CLI and GUI: instantiate with a project path,
then call `build()` or `run()`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from os import environ

from ..pip_install import PipInstaller
from ..platforms import WindowsX86_64Platform
from ..pyproject_toml import PyProjectToml
from .msvc_project_builder import MsvcProjectBuilder


class MsvcProjectError(Exception):
    pass


class MsvcProject:
    builder: MsvcProjectBuilder
    pyproject: PyProjectToml

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        if not (self.project_path / "pyproject.toml").is_file():
            raise MsvcProjectError(f"No pyproject.toml found at {self.project_path}")

        self.pyproject = PyProjectToml(str(self.project_path / "pyproject.toml"))

        kivy_school = self.pyproject.tool.kivy_school
        if kivy_school is None or kivy_school.windows is None:
            raise MsvcProjectError(
                "[tool.kivy-school.windows] section is missing in pyproject.toml"
            )

        self.windows_data = kivy_school.windows
        self.builder = MsvcProjectBuilder(self.pyproject, self.project_path)

    @property
    def build_dir(self) -> Path:
        return self.project_path / "project_dist" / "windows"

    def platform_pre_build_script(self):
        script = self.windows_data.pre_build
        env = {**environ}

        if script:
            cur = Path.cwd()
            env["WHEELHOUSE"] = f"{cur / 'wheelhouse'}"
            match script.suffix:
                case ".py":
                    subprocess.run(
                        ["uv", "run", str(script.absolute())], check=True, env=env
                    )
                case _:
                    subprocess.run([str(script.absolute())], check=True, env=env)

    def install_site_packages(self) -> None:
        """Installs the project and its deps into the MSVC site_packages dir via uv."""
        platform = WindowsX86_64Platform(str(self.project_path))
        Path(platform.site_packages).mkdir(parents=True, exist_ok=True)

        PipInstaller.install(
            uv_src=str(self.project_path),
            platform=platform,
            site_packages=platform.site_packages,
        )

    def generate(self, *args) -> None:
        """Write MSVC files, download python, and zip payload."""
        self.builder.generate(*args)

    def msvc_assemble(self, variant: str = "release", clean: bool = False) -> Path:
        """Locates the local Visual Studio compiler, grabs host Python headers, and links the executable."""
        import sysconfig
        import time

        start_time = time.time()

        vswhere = (
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            / "Microsoft Visual Studio/Installer/vswhere.exe"
        )
        if not vswhere.exists():
            raise MsvcProjectError(
                "Visual Studio Installer not found. Please install MSVC Build Tools."
            )

        result = subprocess.run(
            [str(vswhere), "-latest", "-property", "installationPath"],
            capture_output=True,
            text=True,
            check=True,
        )
        vs_path = Path(result.stdout.strip())
        vcvars = vs_path / "VC/Auxiliary/Build/vcvars64.bat"

        if not vcvars.exists():
            raise MsvcProjectError(
                f"vcvars64.bat not found at {vcvars}. Ensure C++ workloads are installed."
            )

        python_include = Path(sysconfig.get_path("include"))
        python_base = Path(
            sysconfig.get_config_var("installed_base") or sys.base_prefix
        )
        python_libs = python_base / "libs"

        if not python_include.exists() or not python_libs.exists():
            raise MsvcProjectError(
                f"Cannot find host Python headers at {python_include}. Ensure Python was installed with 'Download debugging symbols' and 'Download debug binaries' checked."
            )

        app_name = self.pyproject.project.name
        if getattr(self.pyproject.tool.kivy_school, "app_name", None):
            app_name = self.pyproject.tool.kivy_school.app_name

        output_exe = f"{app_name}.exe"

        require_admin = getattr(self.windows_data, "require_admin", False)
        manifest_flag = (
            "/MANIFESTUAC:\"level='requireAdministrator' uiAccess='false'\""
            if require_admin
            else ""
        )

        subsystem = "WINDOWS" if variant == "release" else "CONSOLE"

        py_ver = self.windows_data.python_version or "3.13.5"
        py_dll_ver = py_ver.replace(".", "")[:3]

        cmd = f"""call "{vcvars}" && cd /d "{self.build_dir}" && rc.exe resources.rc && cl.exe main.c resources.res /I"{python_include}" /link /LIBPATH:"{python_libs}" python3.lib user32.lib delayimp.lib /DELAYLOAD:python3.dll /SUBSYSTEM:{subsystem} {manifest_flag} /OUT:"{output_exe}" """

        print(f"\nBuild with: {cmd.strip()}\n")
        use_shell = sys.platform == "win32"
        compile_result = subprocess.run(cmd, shell=use_shell, env=os.environ.copy())

        if compile_result.returncode != 0:
            raise MsvcProjectError(
                f"MSVC compilation failed with code {compile_result.returncode}"
            )

        exe_path = self.build_dir / output_exe
        if not exe_path.exists():
            raise MsvcProjectError(f"Expected executable not found at {exe_path}")

        elapsed_seconds = time.time() - start_time
        mins, secs = divmod(elapsed_seconds, 60)
        
        if mins > 0:
            time_str = f"{int(mins)}m {secs:.1f}s"
        else:
            time_str = f"{secs:.1f}s"
            
        print(f"\nBUILD SUCCESSFUL in {time_str}")

        return exe_path

    def build(self, variant: str = "release", clean: bool = False) -> Path:
        """Run full pipeline: pre-build -> pip install -> generate -> msvc compile."""
        self.platform_pre_build_script()
        self.install_site_packages()
        self.generate(variant)
        return self.msvc_assemble(variant, clean=clean)

    def run(self) -> None:
        """Executes the newly compiled Windows binary."""
        app_name = self.pyproject.project.name
        if getattr(self.pyproject.tool.kivy_school, "app_name", None):
            app_name = self.pyproject.tool.kivy_school.app_name

        exe_path = self.build_dir / f"{app_name}.exe"
        if not exe_path.exists():
            raise MsvcProjectError("No executable found. Run build first.")

        subprocess.run([str(exe_path)], check=True)
