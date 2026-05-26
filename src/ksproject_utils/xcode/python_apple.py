"""Download/cache Python.xcframework + SDL2 frameworks for Apple builds.

Mirrors:
- ``PSProject/Backends/Sources/Backends/backends/PyFrameworkBackend.swift`` (Apple side)
- ``PSProject/Backends/Sources/Backends/backends/SDL2Backend.swift``

Both artifacts are cached under ``~/.kivyschool/`` (one global cache shared
across projects, matching PSProject's ``Path.ps_support``).
"""

from __future__ import annotations

import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

PY_VERSION = "3.13"
PY_SUB_VERSION = "b11"

_KIVY_SDL2_VERSION = "2.3.10"
_KIVY_SDL2_WHEEL = f"kivy_sdl2-{_KIVY_SDL2_VERSION}-py3-none-any.whl"
_KIVY_SDL2_URL = (
    f"https://api.anaconda.org/download/kivyschool/kivy-sdl2/"
    f"{_KIVY_SDL2_VERSION}/{_KIVY_SDL2_WHEEL}"
)
_KIVY_SDL2_MARKER = ".kivy_sdl2_xcframeworks"


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
    have_ios = (fw / "ios-arm64").exists() and (
        fw / "ios-arm64_x86_64-simulator"
    ).exists()
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


_SLICE_VERSION_MARKER = ".ksproject_slice_version"


def _slice_is_current(dst: Path) -> bool:
    marker = dst / _SLICE_VERSION_MARKER
    return (
        dst.exists()
        and marker.exists()
        and marker.read_text().strip() == f"{PY_VERSION}-{PY_SUB_VERSION}"
    )


def _mark_slice_version(dst: Path) -> None:
    (dst / _SLICE_VERSION_MARKER).write_text(f"{PY_VERSION}-{PY_SUB_VERSION}\n")


def copy_python_xcframework(workdir_frameworks: Path, platforms: list[str]) -> None:
    """Copy the relevant Python.xcframework slices into ``<project>/Frameworks/``.

    Mirrors ``XcodeProjectBuilder.copyPythonLibs``.
    """
    xcfw = python_xcframework()
    workdir_frameworks.mkdir(parents=True, exist_ok=True)
    for p in platforms:
        if p == "iOS":
            for slice_name in ("ios-arm64", "ios-arm64_x86_64-simulator"):
                src = xcfw / slice_name
                dst = workdir_frameworks / slice_name
                if src.exists() and not _slice_is_current(dst):
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    _mark_slice_version(dst)
        elif p == "macOS":
            slice_name = "macos-arm64_x86_64"
            src = xcfw / slice_name
            dst = workdir_frameworks / slice_name
            if src.exists() and not _slice_is_current(dst):
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                _mark_slice_version(dst)
            # PSProject also flattens lib/include from Python.framework/Versions/3.13
            # so build scripts can rsync from "$PROJECT_DIR/Frameworks/macos-arm64_x86_64/lib/".
            py_dir = dst / "Python.framework/Versions" / PY_VERSION
            for sub in ("lib", "include"):
                src_sub = py_dir / sub
                dst_sub = dst / sub
                if src_sub.exists() and not dst_sub.exists():
                    shutil.copytree(src_sub, dst_sub)


def fetch_kivy_sdl2_xcframeworks(workdir_frameworks: Path) -> None:
    """TEMPORARY: download kivy_sdl2 wheel and extract all xcframeworks to Frameworks/.

    Mirrors PSProject SDL2Backend.install().  Remove (or comment out) the call
    once kivy 2.x ships .frameworks/ inside its wheel.
    """
    marker = workdir_frameworks / _KIVY_SDL2_MARKER
    if marker.exists() and marker.read_text().strip() == _KIVY_SDL2_VERSION:
        return

    cache = _support_root() / _KIVY_SDL2_WHEEL
    if not cache.exists():
        print(f"[ksproject] downloading {_KIVY_SDL2_URL}")
        with urllib.request.urlopen(_KIVY_SDL2_URL) as resp, cache.open("wb") as f:
            shutil.copyfileobj(resp, f)

    print(f"[ksproject] extracting xcframeworks from {_KIVY_SDL2_WHEEL}")
    workdir_frameworks.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cache) as zf:
        for info in zf.infolist():
            parts = Path(info.filename).parts
            for i, part in enumerate(parts):
                if part.endswith(".xcframework"):
                    rel = Path(*parts[i:])
                    dst = workdir_frameworks / rel
                    if info.filename.endswith("/"):
                        dst.mkdir(parents=True, exist_ok=True)
                    else:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_bytes(zf.read(info))
                    break

    marker.write_text(f"{_KIVY_SDL2_VERSION}\n")


def copy_site_frameworks(workdir_frameworks: Path, site_packages_root: Path) -> None:
    """Move SDL2*.xcframework from iphoneos site-packages/.frameworks/ into ``<project>/Frameworks/``.

    Frameworks are always taken from the ``iphoneos`` slice (device build) and
    always overwrite anything already in Frameworks/. The ``.frameworks/`` dir is
    then deleted from every slice (simulator's copy is simply discarded).
    """
    if not site_packages_root.is_dir():
        return
    workdir_frameworks.mkdir(parents=True, exist_ok=True)

    iphoneos_frameworks = site_packages_root / "iphoneos" / ".frameworks"
    if iphoneos_frameworks.is_dir():
        for fw_path in iphoneos_frameworks.iterdir():
            if fw_path.suffix == ".xcframework":
                dst = workdir_frameworks / fw_path.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(fw_path), dst)

    for slice_dir in site_packages_root.iterdir():
        fw_dir = slice_dir / ".frameworks"
        if fw_dir.is_dir():
            shutil.rmtree(fw_dir)
