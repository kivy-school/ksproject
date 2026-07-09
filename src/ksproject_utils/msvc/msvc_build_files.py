"""Writes MSVC project files, C bootstraps, and payload zips."""

from __future__ import annotations

import os
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
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(env_dir)
            zip_path.unlink()
            
            for pth_file in env_dir.glob("*._pth"):
                pth_file.unlink()
                print(f"[ksproject] Deleted {pth_file.name} to disable Isolated Mode.")
                
        except Exception as e:
            raise MsvcBuildError(f"Failed to provision Python {python_version}: {e}")
            
        return env_dir

    @staticmethod
    def create_payload_zip(build_dir: Path, app_dir: Path, site_packages_dir: Path, env_dir: Path) -> Path:
        payload_path = build_dir / "payload.zip"
        
        print("[ksproject] Assembling monolithic executable payload...")
        with zipfile.ZipFile(payload_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            
            if env_dir.exists():
                for item in env_dir.iterdir():
                    if item.is_file():
                        zf.write(item, item.name)
            
            if app_dir.exists():
                for root, _, files in os.walk(app_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(app_dir.parent)
                        zf.write(file_path, arcname)
                        
            if site_packages_dir.exists():
                for root, _, files in os.walk(site_packages_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = Path("site-packages") / file_path.relative_to(site_packages_dir)
                        zf.write(file_path, arcname)
                        
        return payload_path

    @staticmethod
    def write_resources_rc(build_dir: Path, payload_path: Path, icon_path: Path | None = None) -> None:
        """Writes the MSVC resource script (.rc)."""
        rc_content = f'101 RCDATA "{payload_path.absolute().as_posix()}"\n'
        
        if icon_path and icon_path.exists():
            rc_content += f'IDI_ICON1 ICON "{icon_path.absolute().as_posix()}"\n'

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

    char dllCmd[1024];
    sprintf_s(dllCmd, 1024, "import os\\nif hasattr(os, 'add_dll_directory'): os.add_dll_directory(r'%s\\\\site-packages\\\\libs')", extractDir);
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
"""
        (build_dir / "main.c").write_text(content, encoding="utf-8")