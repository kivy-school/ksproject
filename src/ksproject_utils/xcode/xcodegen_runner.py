"""Download & cache the XcodeGen CLI binary.

Cached under ``~/.kivyschool/xcodegen/<version>/`` to mirror the existing
``cpython_android.py`` pattern.
"""
from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import urllib.request
import zipfile
from pathlib import Path

XCODEGEN_VERSION = "2.45.4"
XCODEGEN_ARTIFACTBUNDLE_URL = (
    f"https://github.com/yonaskolb/XcodeGen/releases/download/"
    f"{XCODEGEN_VERSION}/xcodegen.artifactbundle.zip"
)


class XcodeGenError(Exception):
    pass


def _cache_root() -> Path:
    return Path.home() / ".kivyschool" / "xcodegen" / XCODEGEN_VERSION


def _binary_path() -> Path:
    """Path to the ``xcodegen`` executable inside the unpacked artifact bundle.

    The artifactbundle layout (Swift Package Manager artifact bundle):
    ``xcodegen.artifactbundle/xcodegen-<version>-macos/bin/xcodegen``
    """
    root = _cache_root() / "xcodegen.artifactbundle"
    candidates = sorted(root.glob("xcodegen-*-macos/bin/xcodegen"))
    if candidates:
        return candidates[0]
    # Fall back to any executable named ``xcodegen`` under the cache.
    fallbacks = sorted(root.rglob("xcodegen"))
    for c in fallbacks:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    raise XcodeGenError(
        f"No xcodegen executable found under {root}"
    )


def _download_and_extract() -> None:
    root = _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    zip_path = root / "xcodegen.artifactbundle.zip"
    print(f"[ksproject] downloading XcodeGen {XCODEGEN_VERSION}...")
    with urllib.request.urlopen(XCODEGEN_ARTIFACTBUNDLE_URL) as resp, zip_path.open("wb") as f:
        shutil.copyfileobj(resp, f)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(root)
    zip_path.unlink()

    # Ensure the extracted binary is executable (zip strips +x on some hosts).
    for exe in root.rglob("xcodegen"):
        if exe.is_file():
            exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class XcodeGenRunner:

    def __init__(self) -> None:
        if platform.system() != "Darwin":
            raise XcodeGenError(
                "XcodeGen is only supported on macOS hosts"
            )
        self._ensure_installed()
        self.binary = _binary_path()

    def _ensure_installed(self) -> None:
        root = _cache_root()
        if root.exists():
            try:
                _binary_path()
                return
            except XcodeGenError:
                pass
        _download_and_extract()

    def generate(self, spec_path: Path, project_dir: Path) -> None:
        """Run ``xcodegen generate --spec <spec> --project <dir>``."""
        result = subprocess.run(
            [
                str(self.binary),
                "generate",
                "--spec", str(spec_path),
                "--project", str(project_dir),
            ],
            cwd=project_dir,
        )
        if result.returncode != 0:
            raise XcodeGenError(
                f"xcodegen exited with code {result.returncode}"
            )
