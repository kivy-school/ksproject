"""Writes MSVC project files, C bootstraps, and payload zips."""

from __future__ import annotations

import os
import subprocess
import shutil
import urllib.request
import zipfile
from pathlib import Path


class MsvcBuildError(Exception):
    pass


class MsvcBuildFiles:

    @staticmethod
    def provision_embeddable_python(build_dir: Path, python_version: str) -> Path:
        """Downloads the official Windows Embeddable Package for Python and disables Isolated Mode."""
        env_dir = build_dir / "windows_env"
        if env_dir.exists() and any(env_dir.iterdir()):
            return env_dir

        env_dir.mkdir(parents=True, exist_ok=True)
        zip_path = build_dir / f"python-{python_version}-embed-amd64.zip"

        url = f"https://www.python.org/ftp/python/{python_version}/python-{python_version}-embed-amd64.zip"
        print(f"[ksproject] Downloading Windows Embeddable Python {python_version}...")

        try:
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(env_dir)
            zip_path.unlink()

            for pth_file in env_dir.glob("*._pth"):
                pth_file.unlink()
                print(f"[ksproject] Deleted {pth_file.name} to disable Isolated Mode.")

        except Exception as e:
            raise MsvcBuildError(f"Failed to provision Python {python_version}: {e}")

        return env_dir

    @staticmethod
    def cythonize_app_module(site_packages_dir: Path, package_name: str) -> None:
        """
        Compiles the application's Python source files into Cython extensions (.pyd)
        and removes the original .py and generated .c files to hide the source code.
        """
        app_dir = site_packages_dir / package_name

        if not app_dir.exists():
            print(
                f"[ksproject] App module not found at {app_dir}, skipping Cythonization."
            )
            return

        try:
            import Cython  # noqa: F401
        except ImportError:
            print(
                "[ksproject] Warning: Cython is not installed. Skipping source obfuscation."
            )
            return

        print(f"[ksproject] Cythonizing app module '{package_name}' to hide source...")

        setup_py_path = site_packages_dir / "setup.py"
        setup_py_content = f"""
from setuptools import setup
from Cython.Build import cythonize
from pathlib import Path

package_name = "{package_name}"
source_files = [str(p) for p in Path(package_name).rglob('*.py') if p.name not in ('__init__.py', '__main__.py')]

setup(
    ext_modules=cythonize(
        source_files,
        compiler_directives={{'language_level': '3', 'always_allow_keywords': True}},
        quiet=True
    )
)
"""
        setup_py_path.write_text(setup_py_content, encoding="utf-8")

        import sys

        print("            Building C extensions (this may take a moment)...")
        result = subprocess.run(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=site_packages_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("[ksproject] Error during Cythonization:")
            print(result.stderr)
            setup_py_path.unlink(missing_ok=True)
            return

        print("            Cythonization successful. Scrubbing source files...")

        for py_file in app_dir.rglob("*.py"):
            py_file.unlink(missing_ok=True)

        for c_file in app_dir.rglob("*.c"):
            c_file.unlink(missing_ok=True)

        setup_py_path.unlink(missing_ok=True)

        build_dir = site_packages_dir / "build"
        if build_dir.exists() and build_dir.is_dir():
            shutil.rmtree(build_dir)

        print("[ksproject] Source code hidden successfully.")

    @staticmethod
    def create_payload_zip(
        package_name: str,
        build_dir: Path,
        site_packages_dir: Path,
        env_dir: Path,
        python_version: str,
        optimize: bool = True,
    ) -> Path:
        payload_path = build_dir / "payload.zip"
        staging_dir = build_dir / "payload_staging"

        print("[ksproject] Staging files for monolithic payload...")
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True)

        staged_sp = staging_dir / "site-packages"
        if site_packages_dir.exists():
            shutil.copytree(site_packages_dir, staged_sp)

        MsvcBuildFiles.cythonize_app_module(staged_sp, package_name)

        if optimize:
            print(
                f"[ksproject] Resolving uv Python {python_version} executable path..."
            )
            try:
                python_exe = subprocess.check_output(
                    ["uv", "python", "find", python_version],
                    text=True,
                    creationflags=0x08000000,
                ).strip()

                print(f"[ksproject] Byte-compiling payload using: {python_exe}")

                subprocess.run(
                    [
                        python_exe,
                        "-m",
                        "compileall",
                        "-b",
                        "-o",
                        "2",
                        "-j",
                        "0",
                        "-q",
                        str(staging_dir),
                    ],
                    check=False,
                    creationflags=0x08000000,
                )

            except (subprocess.CalledProcessError, FileNotFoundError):
                print(
                    f"[ksproject] Failed to find Python {python_version} via uv. Skipping optimization."
                )

        print("[ksproject] Stripping junk files and unneeded source code...")
        junk_exts = {
            ".pyi",
            ".c",
            ".cpp",
            ".h",
            ".pyx",
            ".pxd",
            ".md",
            ".rst",
            ".chm",
            ".html",
            ".htm",
        }
        if optimize:
            junk_exts.add(".py")
        junk_dirs = {
            "tests",
            "test",
            "docs",
            "doc",
            "examples",
            "example",
            "tutorials",
            "benchmarks",
            "perf",
            ".mypy_cache",
            ".pytest_cache",
            "__pycache__",
            "bin",
            "unittest",
            "share",
            "demos",
        }

        for root, dirs, files in os.walk(staging_dir, topdown=False):
            for file in files:
                p = Path(root) / file
                if p.suffix in junk_exts:
                    try:
                        p.unlink()
                    except:
                        pass

            for d in dirs:
                if d.lower() in junk_dirs:
                    p = Path(root) / d
                    try:
                        shutil.rmtree(p)
                    except:
                        pass

        print("[ksproject] Assembling optimized zip archive...")
        with zipfile.ZipFile(payload_path, "w", zipfile.ZIP_DEFLATED) as zf:

            if env_dir.exists():
                for item in env_dir.iterdir():
                    if item.is_file():
                        zf.write(item, item.name)

            for root, _, files in os.walk(staging_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(staging_dir)
                    zf.write(file_path, arcname)

        return payload_path

    @staticmethod
    def write_resources_rc(
        build_dir: Path,
        payload_path: Path,
        icon_path: Path | None = None,
        require_admin: bool = False,
    ) -> None:
        """Writes the MSVC resource script (.rc) and UAC manifest."""
        rc_content = f'101 RCDATA "{payload_path.absolute().as_posix()}"\n'

        if icon_path and icon_path.exists():
            rc_content += f'IDI_ICON1 ICON "{icon_path.absolute().as_posix()}"\n'

        if require_admin:
            manifest_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
      <windowsSettings>
          <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
          <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>
      </windowsSettings>
  </application>
</assembly>"""
            manifest_path = build_dir / "app.manifest"
            manifest_path.write_text(manifest_content, encoding="utf-8")
            rc_content += f'1 24 "{manifest_path.absolute().as_posix()}"\n'

        (build_dir / "resources.rc").write_text(rc_content, encoding="utf-8")

    @staticmethod
    def write_main_c(build_dir: Path, package_name: str, python_version: str) -> None:
        """Generates the C bootstrap code to extract the payload and initialize Python."""

        py_dll_ver = python_version.replace(".", "")[:3]
        py_zip = f"python{py_dll_ver}.zip"

        content = f"""\
#define PY_SSIZE_T_CLEAN
#include <windows.h>
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>

void ExtractPayload(const char* zipPath) {{
    HRSRC hRes = FindResource(NULL, MAKEINTRESOURCE(101), RT_RCDATA); 
    if (!hRes) return;
    HGLOBAL hMem = LoadResource(NULL, hRes);
    DWORD size = SizeofResource(NULL, hRes);
    void* data = LockResource(hMem);

    FILE* f = fopen(zipPath, "wb");
    if (f) {{
        fwrite(data, 1, size, f);
        fclose(f);
    }}
}}

void RunCommandSilent(const char* cmd) {{
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE; // Ensure no window is shown
    ZeroMemory(&pi, sizeof(pi));

    char cmdBuf[2048];
    sprintf_s(cmdBuf, 2048, "cmd.exe /c %s", cmd);

    if (CreateProcessA(NULL, cmdBuf, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {{
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }}
}}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {{
    char tempPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tempPath);

    char zipPath[MAX_PATH];
    sprintf_s(zipPath, MAX_PATH, "%s%s_payload.zip", tempPath, "{package_name}");

    char extractDir[MAX_PATH];
    sprintf_s(extractDir, MAX_PATH, "%s%s_env", tempPath, "{package_name}");

    ExtractPayload(zipPath);

    char extractCmd[1024];
    sprintf_s(extractCmd, 1024, "mkdir \\"%s\\" 2>nul & tar -xf \\"%s\\" -C \\"%s\\"", extractDir, zipPath, extractDir);

    RunCommandSilent(extractCmd);

    SetDllDirectoryA(extractDir);

    wchar_t libsDir[MAX_PATH];
    swprintf_s(libsDir, MAX_PATH, L"%hs\\\\site-packages\\\\libs", extractDir);
    SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS | LOAD_LIBRARY_SEARCH_USER_DIRS);
    AddDllDirectory(libsDir);

    char pyPath[2048];
    sprintf_s(pyPath, 2048, "%s\\\\{py_zip};%s;%s\\\\site-packages;%s\\\\{package_name}", extractDir, extractDir, extractDir, extractDir);
    
    wchar_t wPyPath[2048];
    size_t converted;
    mbstowcs_s(&converted, wPyPath, 2048, pyPath, _TRUNCATE);
    Py_SetPath(wPyPath);

    Py_Initialize();

    char dllCmd[2048];
    sprintf_s(dllCmd, 2048, 
        "import os, sys\\n"
        "env_dir = r'''%s'''\\n"
        "sys.prefix = os.path.join(env_dir, 'site-packages')\\n"
        "sys.exec_prefix = sys.prefix\\n"
        "os.environ['KIVY_DEPS_ROOT'] = sys.prefix\\n"
        "libs_dir = os.path.join(sys.prefix, 'libs')\\n"
        "if os.path.exists(libs_dir) and hasattr(os, 'add_dll_directory'):\\n"
        "    os.add_dll_directory(libs_dir)\\n", 
        extractDir);
    PyRun_SimpleString(dllCmd);
    
    PyObject *runpy = PyImport_ImportModule("runpy");
    if (!runpy) {{
        MessageBoxA(NULL, "Failed to import runpy module!", "Fatal Error", MB_OK | MB_ICONERROR);
        Py_FinalizeEx();
        return 1;
    }}

    PyObject *func = PyObject_GetAttrString(runpy, "run_module");
    PyObject *args_tuple = PyTuple_Pack(1, PyUnicode_FromString("{package_name}"));
    PyObject *kwargs = Py_BuildValue("{{s:s, s:i}}", "run_name", "__main__", "alter_sys", 1);

    PyObject *result = PyObject_Call(func, args_tuple, kwargs);

    if (!result) {{
        if (PyErr_Occurred()) {{
            PyErr_Print();
        }}
        MessageBoxA(NULL, "The Python application crashed! Build in debug mode to see the console trace.", "Fatal Error", MB_OK | MB_ICONERROR);
    }} else {{
        Py_DECREF(result);
    }}

    Py_DECREF(args_tuple);
    Py_DECREF(kwargs);
    Py_DECREF(func);
    Py_DECREF(runpy);

    Py_FinalizeEx();
    return 0;
}}

int main(int argc, char** argv) {{
    return WinMain(GetModuleHandle(NULL), NULL, GetCommandLineA(), SW_SHOWDEFAULT);
}}
"""
        (build_dir / "main.c").write_text(content, encoding="utf-8")
