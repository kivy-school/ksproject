"""Download/cache Python.xcframework + SDL2 frameworks for Apple builds.

Mirrors:
- ``PSProject/Backends/Sources/Backends/backends/PyFrameworkBackend.swift`` (Apple side)
- ``PSProject/Backends/Sources/Backends/backends/SDL2Backend.swift``

Both artifacts are cached under ``~/.kivyschool/`` (one global cache shared
across projects, matching PSProject's ``Path.ps_support``).
"""
from __future__ import annotations

import plistlib
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PY_VERSION = "3.13"
PY_SUB_VERSION = "b11"

# Used when the app project doesn't pin an exact patch release in
# .python-version. Must have an entry in ``apple_python_versions``.
DEFAULT_APPLE_PY_VERSION = "3.13.11"

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


def apple_python_cache_root() -> Path:
    root = Path.home() / ".kivyschool" / "apple" / "python"
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


_SLICE_VERSION_MARKER = ".ksproject_slice_version"


def _slice_is_current(dst: Path) -> bool:
    marker = dst / _SLICE_VERSION_MARKER
    return dst.exists() and marker.exists() and marker.read_text().strip() == f"{PY_VERSION}-{PY_SUB_VERSION}"


def _mark_slice_version(dst: Path) -> None:
    (dst / _SLICE_VERSION_MARKER).write_text(f"{PY_VERSION}-{PY_SUB_VERSION}\n")


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
                if src.exists() and not _slice_is_current(dst):
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst, symlinks=True)
                    _mark_slice_version(dst)
        elif p == "macOS":
            slice_name = "macos-arm64_x86_64"
            src = xcfw / slice_name
            dst = workdir_support / slice_name
            if src.exists() and not _slice_is_current(dst):
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, symlinks=True)
                _mark_slice_version(dst)
            # PSProject also flattens lib/include from Python.framework/Versions/3.13
            # so build scripts can rsync from "$PROJECT_DIR/Support/macos-arm64_x86_64/lib/".
            py_dir = dst / "Python.framework/Versions" / PY_VERSION
            for sub in ("lib", "include"):
                src_sub = py_dir / sub
                dst_sub = dst / sub
                if src_sub.exists() and not dst_sub.exists():
                    shutil.copytree(src_sub, dst_sub, symlinks=True)


def fetch_kivy_sdl2_xcframeworks(workdir_support: Path) -> None:
    """TEMPORARY: download kivy_sdl2 wheel and extract all xcframeworks to Support/.

    Mirrors PSProject SDL2Backend.install().  Remove (or comment out) the call
    once kivy 2.x ships .frameworks/ inside its wheel.
    """
    marker = workdir_support / _KIVY_SDL2_MARKER
    if marker.exists() and marker.read_text().strip() == _KIVY_SDL2_VERSION:
        return

    cache = _support_root() / _KIVY_SDL2_WHEEL
    if not cache.exists():
        print(f"[ksproject] downloading {_KIVY_SDL2_URL}")
        with urllib.request.urlopen(_KIVY_SDL2_URL) as resp, cache.open("wb") as f:
            shutil.copyfileobj(resp, f)

    print(f"[ksproject] extracting xcframeworks from {_KIVY_SDL2_WHEEL}")
    workdir_support.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cache) as zf:
        for info in zf.infolist():
            parts = Path(info.filename).parts
            for i, part in enumerate(parts):
                if part.endswith(".xcframework"):
                    rel = Path(*parts[i:])
                    dst = workdir_support / rel
                    if info.filename.endswith("/"):
                        dst.mkdir(parents=True, exist_ok=True)
                    else:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_bytes(zf.read(info))
                    break

    marker.write_text(f"{_KIVY_SDL2_VERSION}\n")


def copy_site_frameworks(workdir_support: Path, site_packages_root: Path) -> None:
    """Move xcframeworks from site-packages/.frameworks/ into ``<project>/Support/``.

    kivy ships xcframeworks inside each pip-installed slice under
    ``.frameworks/``.  The bundles are identical multi-arch xcframeworks across
    all slices (iphoneos, iphonesimulator, …), so we iterate every slice:
    move xcframeworks to Support/ (overwriting), then delete the now-empty
    ``.frameworks/`` dir.  Whichever slice is processed last wins, but since
    the content is identical it doesn't matter.
    """
    if not site_packages_root.is_dir():
        return
    workdir_support.mkdir(parents=True, exist_ok=True)

    for slice_dir in sorted(site_packages_root.iterdir()):
        fw_dir = slice_dir / ".frameworks"
        if not fw_dir.is_dir():
            continue
        for fw_path in fw_dir.iterdir():
            if fw_path.suffix == ".xcframework":
                dst = workdir_support / fw_path.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(fw_path), dst)
        shutil.rmtree(fw_dir)

class BeewarePythonVersion:
    beeware: str
    major: int
    minor: int

    def __init__(self, beeware: str, major: int, minor: int):
        self.beeware = beeware
        self.major = major
        self.minor = minor

    def url_for(self, platform: str) -> str:
        b = self.beeware
        major = self.major
        return f"https://github.com/beeware/Python-Apple-support/releases/download/3.{major}-{b}/Python-3.{major}-{platform}-support.{b}.tar.gz"

    @property
    def macos_url(self) -> str:
        return self.url_for("macOS")

    @property
    def ios_url(self) -> str:
        return self.url_for("iOS")

    @property
    def url(self) -> str:
        return self.macos_url

apple_python_versions = [
    BeewarePythonVersion(
        "b13", 13, 11
    ),
    BeewarePythonVersion(
        "b14", 13, 14
    ),
    BeewarePythonVersion(
        "b9", 14, 2
    ),
    BeewarePythonVersion(
        "b10", 14, 6
    )
]


def get_beeware_version(major: int, minor: int) -> BeewarePythonVersion | None:
    for fw in apple_python_versions:
        if fw.major == major and fw.minor == minor: return fw
    return None


def supported_apple_py_versions() -> list[str]:
    """Exact Python versions BeeWare ships Python-Apple-support builds for."""
    return [f"3.{fw.major}.{fw.minor}" for fw in apple_python_versions]


def unsupported_apple_py_error(version: str) -> AppleSupportError:
    return AppleSupportError(
        f"Python {version} has no BeeWare Python-Apple-support build. "
        f"Supported versions: {', '.join(supported_apple_py_versions())} — "
        f"pin one of these in .python-version (or use a bare major.minor "
        f"like '3.13' to get the default {DEFAULT_APPLE_PY_VERSION})."
    )

class ApplePythonFramework:

    support_root: Path
    version: str
    major_version: int
    minor_version: int

    def __init__(self, support_root: Path, version: str = DEFAULT_APPLE_PY_VERSION):
        self.support_root = support_root
        self.version = version
        main_ver, maj_ver, min_ver = [int(x) for x in version.split(".")]
        self.major_version = maj_ver
        self.minor_version = min_ver

    @property
    def framework(self) -> BeewarePythonVersion | None:
        return get_beeware_version(self.major_version, self.minor_version)

    @property
    def xcframework_path(self) -> Path:
        return self.support_root / self.version / "Python.xcframework"

    def ensure_merged(self) -> Path:
        fw = self.xcframework_path
        if fw.exists():
            return fw
        return self.merge_frameworks()

    def install_to(self, destination: Path) -> None:
        dst = destination / "Python.xcframework"
        if dst.exists():
            return
        shutil.copytree(self.ensure_merged(), dst, symlinks=True)

    def download(self, url: str, destination: Path) -> None:
        tar_name = url.rsplit("/", 1)[-1]
        tar_path = destination / tar_name
        destination.mkdir(parents=True, exist_ok=True)
        print(f"[ksproject] downloading {url}")
        with urllib.request.urlopen(url) as resp, tar_path.open("wb") as f:
            shutil.copyfileobj(resp, f)
        print(f"[ksproject] extracting {tar_name}")
        with tarfile.open(tar_path) as tf:
            tf.extractall(destination)
        tar_path.unlink()

    def download_macos(self, destination: Path) -> None:
        fw = self.framework
        if not fw:
            raise unsupported_apple_py_error(self.version)
        self.download(fw.macos_url, destination)

    def download_ios(self, destination: Path) -> None:
        fw = self.framework
        if not fw:
            raise unsupported_apple_py_error(self.version)
        self.download(fw.ios_url, destination)

    def merge_frameworks(self) -> Path:
        fw_dst = self.xcframework_path
        fw_dst.mkdir(parents=True, exist_ok=True)

        merged_libraries = []
        base_plist: dict = {}

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self.download_macos(tmp_path / "macos")
            self.download_ios(tmp_path / "ios")
            for platform_tmp in (tmp_path / "macos", tmp_path / "ios"):
                xcfw_src = platform_tmp / "Python.xcframework"
                if not xcfw_src.is_dir():
                    continue
                plist_path = xcfw_src / "Info.plist"
                if not plist_path.exists():
                    continue
                with plist_path.open("rb") as f:
                    src_plist = plistlib.load(f)
                merged_libraries.extend(src_plist.get("AvailableLibraries", []))
                base_plist = src_plist
                slice_names = {lib["LibraryIdentifier"] for lib in src_plist.get("AvailableLibraries", [])}
                for lib in src_plist.get("AvailableLibraries", []):
                    slice_name = lib["LibraryIdentifier"]
                    src_slice = xcfw_src / slice_name
                    if not src_slice.is_dir():
                        continue
                    dst_slice = fw_dst / slice_name
                    if dst_slice.exists():
                        shutil.rmtree(dst_slice)
                    shutil.copytree(src_slice, dst_slice, symlinks=True)
                for entry in xcfw_src.iterdir():
                    if entry.name in slice_names or entry.name == "Info.plist":
                        continue
                    dst_entry = fw_dst / entry.name
                    if entry.is_dir():
                        if not dst_entry.exists():
                            shutil.copytree(entry, dst_entry, symlinks=True)
                    else:
                        if not dst_entry.exists():
                            shutil.copy2(entry, dst_entry)

        base_plist["AvailableLibraries"] = merged_libraries
        with (fw_dst / "Info.plist").open("wb") as f:
            plistlib.dump(base_plist, f)

        py_ver = f"3.{self.major_version}"
        py_lib = fw_dst / "macos-arm64_x86_64/Python.framework/Versions" / py_ver / "lib"
        for stale in (
            py_lib / f"libpython{py_ver}.dylib",
            py_lib / f"python{py_ver}/config-{py_ver}-darwin",
        ):
            if stale.is_symlink() or stale.is_file():
                stale.unlink(missing_ok=True)
            elif stale.is_dir():
                shutil.rmtree(stale, ignore_errors=True)

        for lib in merged_libraries:
            slice_dir = fw_dst / lib["LibraryIdentifier"]
            fw_bundle = slice_dir / lib["LibraryPath"]
            modules_dir = fw_bundle / "Modules"
            src_map = fw_bundle / "Headers" / "module.modulemap"
            if src_map.exists():
                modules_dir.mkdir(exist_ok=True)
                dst_map = modules_dir / "module.modulemap"
                content = src_map.read_text().replace("module Python {", "framework module Python {", 1)
                dst_map.write_text(content)

        return fw_dst