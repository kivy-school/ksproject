"""Download/cache Python.xcframework + SDL2 frameworks for Apple builds.

Mirrors:
- ``PSProject/Backends/Sources/Backends/backends/PyFrameworkBackend.swift`` (Apple side)
- ``PSProject/Backends/Sources/Backends/backends/SDL2Backend.swift``

Both artifacts are cached under ``~/.kivyschool/`` (one global cache shared
across projects, matching PSProject's ``Path.ps_support``).
"""
from __future__ import annotations

import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from ..tools import get_uv

PY_VERSION = "3.13"
PY_SUB_VERSION = "b11"

KIVYSCHOOL_SIMPLE = "https://pypi.anaconda.org/kivyschool/simple"


class AppleSupportError(Exception):
    pass


def _support_root() -> Path:
    root = Path.home() / ".kivyschool" / "apple_support"
    root.mkdir(parents=True, exist_ok=True)
    return root


def python_xcframework() -> Path:
    """Return the cached ``Python.xcframework`` directory, downloading if needed.

    Downloads BeeWare's Python-Apple-support tarballs for iOS and macOS and
    untars them in-place. The two tarballs merge into a single xcframework
    bundle alongside each other.
    """
    support = _support_root()
    fw = support / "Python.xcframework"
    # We consider it "fully installed" once both iOS slice dirs exist.
    have_ios = (fw / "ios-arm64").exists() and (fw / "ios-arm64_x86_64-simulator").exists()
    have_macos = (fw / "macos-arm64_x86_64").exists()
    if have_ios and have_macos:
        return fw

    for plat in ("iOS", "macOS"):
        if plat == "iOS" and have_ios:
            continue
        if plat == "macOS" and have_macos:
            continue
        _download_python_support(support, plat)

    # macOS housekeeping (mirrors PyFrameworkBackend.swift): remove dylib + config dir.
    py_lib = fw / "macos-arm64_x86_64/Python.framework/Versions" / PY_VERSION / "lib"
    for stale in (
        py_lib / f"libpython{PY_VERSION}.dylib",
        py_lib / f"python{PY_VERSION}/config-{PY_VERSION}-darwin",
    ):
        if stale.is_symlink() or stale.is_file():
            stale.unlink(missing_ok=True)
        elif stale.is_dir():
            shutil.rmtree(stale, ignore_errors=True)

    return fw


def _download_python_support(support: Path, platform_name: str) -> None:
    url = (
        f"https://github.com/beeware/Python-Apple-support/releases/download/"
        f"{PY_VERSION}-{PY_SUB_VERSION}/"
        f"Python-{PY_VERSION}-{platform_name}-support.{PY_SUB_VERSION}.tar.gz"
    )
    tar_path = support / f"Python-{PY_VERSION}-{platform_name}-support.tar.gz"
    print(f"[ksproject] downloading {url}")
    with urllib.request.urlopen(url) as resp, tar_path.open("wb") as f:
        shutil.copyfileobj(resp, f)
    print(f"[ksproject] extracting {tar_path.name}")
    with tarfile.open(tar_path) as tf:
        tf.extractall(support)
    tar_path.unlink()


def sdl2_frameworks() -> Path:
    """Return the cache dir containing the SDL2 xcframeworks, pip-installing if needed.

    ``kivy_sdl2`` is a marker package on the kivyschool channel that ships the
    four ``SDL2*.xcframework`` bundles. ``-t <dir>`` makes pip extract them
    directly under that dir.
    """
    support = _support_root()
    dest = support / "sdl2_frameworks"
    if (dest / "SDL2.xcframework").exists():
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    uv = get_uv()
    if uv is None:
        raise AppleSupportError("`uv` not found in PATH; cannot install kivy_sdl2")
    result = subprocess.run(
        [
            uv, "pip", "install",
            "kivy_sdl2",
            "--extra-index-url", KIVYSCHOOL_SIMPLE,
            "--index-strategy", "unsafe-best-match",
            "--target", str(dest),
        ],
    )
    if result.returncode != 0:
        raise AppleSupportError(
            f"`uv pip install kivy_sdl2` exited with code {result.returncode}"
        )
    if not (dest / "SDL2.xcframework").exists():
        raise AppleSupportError(
            f"kivy_sdl2 installed but no SDL2.xcframework found at {dest}"
        )
    return dest


def copy_python_xcframework(workdir_support: Path, platforms: list[str]) -> None:
    """Copy the relevant Python.xcframework slices into ``<project>/Support/``.

    Mirrors ``XcodeProjectBuilder.copyPythonLibs``.
    """
    xcfw = python_xcframework()
    workdir_support.mkdir(parents=True, exist_ok=True)
    for p in platforms:
        if p == "iOS":
            for slice_name in ("ios-arm64", "ios-arm64_x86_64-simulator"):
                src = xcfw / slice_name
                dst = workdir_support / slice_name
                if not dst.exists() and src.exists():
                    shutil.copytree(src, dst)
        elif p == "macOS":
            slice_name = "macos-arm64_x86_64"
            src = xcfw / slice_name
            dst = workdir_support / slice_name
            if not dst.exists() and src.exists():
                shutil.copytree(src, dst)
            # PSProject also flattens lib/include from Python.framework/Versions/3.13
            # so build scripts can rsync from "$PROJECT_DIR/Support/macos-arm64_x86_64/lib/".
            py_dir = dst / "Python.framework/Versions" / PY_VERSION
            for sub in ("lib", "include"):
                src_sub = py_dir / sub
                dst_sub = dst / sub
                if src_sub.exists() and not dst_sub.exists():
                    shutil.copytree(src_sub, dst_sub)


def copy_sdl2_frameworks(workdir_support: Path) -> None:
    """Copy SDL2*.xcframework bundles into ``<project>/Support/``."""
    src_root = sdl2_frameworks()
    workdir_support.mkdir(parents=True, exist_ok=True)
    for name in ("SDL2", "SDL2_image", "SDL2_mixer", "SDL2_ttf"):
        src = src_root / f"{name}.xcframework"
        dst = workdir_support / f"{name}.xcframework"
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)
