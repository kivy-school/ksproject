"""CPython-for-Android build helper. Ported from PyFrameworkBackend.installAndroid."""
from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


ANDROID_VERSION = "3.13.8"
PY_VERSION = "3.13"

# Anaconda channel hosting prebuilt libpython-<ver>-<rev>-py3-none-android_*.whl
PREBUILT_INDEX_URL = os.environ.get(
    "KIVYSCHOOL_PREBUILT_INDEX",
    "https://pypi.anaconda.org/kivyschool/simple/libpython/",
)
PREBUILT_BUILD_TAG = os.environ.get("KIVYSCHOOL_PREBUILT_BUILD", "0")
PREBUILT_API = int(os.environ.get("KIVYSCHOOL_PREBUILT_API", "21"))


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
    # Try the anaconda.org/kivyschool prebuilt first. Each ABI's wheel ships
    # the full cross-build prefix (+ shared pure-py stdlib), so we just extract
    # into the same path install_cpython_android() would otherwise produce.
    remaining = [
        a for a in archs if not _try_install_prebuilt(working_dir, a, android_version, py_version)
    ]
    if not remaining:
        return

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

    for arch in remaining:
        triple = android_triple(arch)
        prefix = cpython_dir / "cross-build" / triple / "prefix"
        if (prefix / f"lib/libpython{py_version}.so").exists():
            print(f"CPython {py_version} for {arch} already built")
            continue

        print(f"Building CPython {android_version} for {arch} ({triple})...")
        _run_android(["configure-host", triple], cpython_dir, env)
        _run_android(["make-host", triple], cpython_dir, env)
        print(f"CPython {py_version} for {arch} built successfully")


def _try_install_prebuilt(
    working_dir: Path,
    arch: str,
    android_version: str,
    py_version: str,
) -> bool:
    """Download + extract a prebuilt libpython wheel for ``arch``.

    Returns True on success, False if anything (network, missing file, bad
    archive) goes wrong so the caller can fall back to building from source.
    Honors ``KIVYSCHOOL_PREBUILT_DISABLE=1`` to force-skip.
    Honors ``KIVYSCHOOL_PREBUILT_FILE_<ARCH>`` (e.g. for arm64-v8a:
    ``KIVYSCHOOL_PREBUILT_FILE_ARM64_V8A=/path/to.whl``) so CI / dev can point
    at a local wheel without hitting the index.
    """
    if os.environ.get("KIVYSCHOOL_PREBUILT_DISABLE") == "1":
        return False

    prefix = android_prefix(working_dir, arch, android_version)
    libpy = prefix / "lib" / f"libpython{py_version}.so"
    if libpy.exists():
        return True

    local_env = f"KIVYSCHOOL_PREBUILT_FILE_{arch.upper().replace('-', '_')}"
    local_path = os.environ.get(local_env)

    wheel_name = (
        f"libpython-{android_version}-{PREBUILT_BUILD_TAG}-py3-none-"
        f"android_{PREBUILT_API}_{arch.replace('-', '_')}.whl"
    )
    wheel_url = (
        PREBUILT_INDEX_URL.rstrip("/") + f"/{android_version}/" + wheel_name
    )

    cache_dir = working_dir / ".kivyschool" / "prebuilt-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    wheel_cache = cache_dir / wheel_name

    try:
        if local_path:
            src = Path(local_path)
            if not src.exists():
                print(f"  prebuilt: {local_env}={src} does not exist")
                return False
            print(f"  prebuilt: using local wheel {src}")
            wheel_cache = src
        elif not wheel_cache.exists():
            print(f"  prebuilt: fetching {wheel_url}")
            urllib.request.urlretrieve(wheel_url, wheel_cache)

        with zipfile.ZipFile(wheel_cache) as zf:
            names = zf.namelist()
            arch_prefix = f"libpython/prefix/{arch}/"
            stdlib_prefix = f"libpython/stdlib/python{py_version}/"
            if not any(n.startswith(arch_prefix) for n in names):
                print(f"  prebuilt: wheel missing {arch_prefix} entries")
                return False

            prefix.mkdir(parents=True, exist_ok=True)
            stdlib_dst = prefix / "lib" / f"python{py_version}"
            stdlib_dst.mkdir(parents=True, exist_ok=True)

            for name in names:
                if name.endswith("/"):
                    continue
                if name.startswith(arch_prefix):
                    rel = name[len(arch_prefix):]
                    dst = prefix / rel
                elif name.startswith(stdlib_prefix):
                    rel = name[len(stdlib_prefix):]
                    dst = stdlib_dst / rel
                else:
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as src_f, open(dst, "wb") as dst_f:
                    shutil.copyfileobj(src_f, dst_f)

        if not libpy.exists():
            print(f"  prebuilt: extraction did not produce {libpy}")
            return False
        print(f"  prebuilt: installed CPython {android_version} for {arch}")
        return True
    except (urllib.error.URLError, zipfile.BadZipFile, OSError) as exc:
        print(f"  prebuilt: fetch failed for {arch}: {exc}")
        return False


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
