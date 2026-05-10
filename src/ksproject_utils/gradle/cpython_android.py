"""CPython-for-Android build helper. Ported from PyFrameworkBackend.installAndroid."""
from __future__ import annotations

import os
import subprocess
import tarfile
import urllib.request
from pathlib import Path


ANDROID_VERSION = "3.13.8"
PY_VERSION = "3.13"


_TRIPLES = {
    "arm64-v8a": "aarch64-linux-android",
    "x86_64": "x86_64-linux-android",
}


class CPythonBuildError(Exception):
    pass


def android_triple(arch: str) -> str:
    if arch not in _TRIPLES:
        raise CPythonBuildError(f"Unsupported Android arch: {arch}")
    return _TRIPLES[arch]


def android_prefix(
    working_dir: Path, arch: str, android_version: str = ANDROID_VERSION
) -> Path:
    triple = android_triple(arch)
    return (
        working_dir
        / ".kivyschool"
        / f"Python-{android_version}"
        / "cross-build"
        / triple
        / "prefix"
    )


def install_cpython_android(
    working_dir: Path,
    archs: list[str],
    sdk: str | None,
    ndk: str | None,
    java: str | None,
    py_version: str = PY_VERSION,
    android_version: str = ANDROID_VERSION,
) -> None:
    ks_dir = working_dir / ".kivyschool"
    cpython_dir = ks_dir / f"Python-{android_version}"

    if not cpython_dir.exists():
        ks_dir.mkdir(parents=True, exist_ok=True)
        print(f"Downloading CPython {android_version} source...")
        url = (
            f"https://www.python.org/ftp/python/{android_version}"
            f"/Python-{android_version}.tgz"
        )
        tar_path = ks_dir / f"Python-{android_version}.tgz"
        urllib.request.urlretrieve(url, tar_path)
        with tarfile.open(tar_path) as tf:
            tf.extractall(ks_dir)
        tar_path.unlink(missing_ok=True)

    env = os.environ.copy()
    if sdk:
        env["ANDROID_HOME"] = sdk
    if ndk:
        env["ANDROID_NDK_ROOT"] = ndk
    if java:
        env["JAVA_HOME"] = java

    # configure-build must run once before any configure-host
    build_dir = cpython_dir / "cross-build" / "build"
    if not build_dir.exists():
        print("Configuring CPython build-machine interpreter...")
        _run_android(["configure-build"], cpython_dir, env)
        print("Building CPython build-machine interpreter...")
        _run_android(["make-build"], cpython_dir, env)

    for arch in archs:
        triple = android_triple(arch)
        prefix = cpython_dir / "cross-build" / triple / "prefix"
        if (prefix / f"lib/libpython{py_version}.so").exists():
            print(f"CPython {py_version} for {arch} already built")
            continue

        print(f"Building CPython {android_version} for {arch} ({triple})...")
        _run_android(["configure-host", triple], cpython_dir, env)
        _run_android(["make-host", triple], cpython_dir, env)
        print(f"CPython {py_version} for {arch} built successfully")


def _run_android(args: list[str], cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        ["python3", "Android/android.py", *args],
        cwd=cwd,
        env=env,
    )
    if result.returncode != 0:
        raise CPythonBuildError(
            f"CPython Android build step failed: {' '.join(args)}"
        )
