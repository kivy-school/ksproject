"""Resolve the app project's pinned Python version from ``.python-version``.

``SupportedPythonVersion`` is the single global list of exact Python
versions ksproject supports — controlled by what BeeWare's
Python-Apple-support ships (Android prebuilts/official binaries follow the
same versions). A project may pin an exact patch release (``3.13.11``);
that version then drives everything: the BeeWare framework, the CPython
Android build, and every ``uv run --python`` pin in generated build
scripts. A bare major.minor pin (``3.13``) or a missing file means "use
ksproject's built-in defaults". Anything not covered by the enum raises
``UnsupportedPythonVersionError`` immediately.
"""
from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

# Accepts "3.13", "3.13.11" and uv's long form "cpython-3.13.11-macos-...".
_PIN_RE = re.compile(r"^(?:cpython-)?(\d+)\.(\d+)(?:\.(\d+))?")


class SupportedPythonVersion(StrEnum):
    """Exact Python versions supported across apple + android.

    Gated by BeeWare Python-Apple-support releases — add a member here
    (and its beeware tag in ``python_apple._BEEWARE_TAGS``) when BeeWare
    ships a new build.
    """

    V3_13_8 = "3.13.8"
    V3_13_11 = "3.13.11"
    V3_13_14 = "3.13.14"
    V3_14_2 = "3.14.2"
    V3_14_6 = "3.14.6"

    @classmethod
    def values(cls) -> list[str]:
        return [m.value for m in cls]

    @classmethod
    def major_minors(cls) -> list[str]:
        seen: list[str] = []
        for m in cls:
            mm = m.value.rsplit(".", 1)[0]
            if mm not in seen:
                seen.append(mm)
        return seen

    @classmethod
    def latest_for(cls, major_minor: str) -> str | None:
        """Newest supported patch release of a major.minor family."""
        patches = [
            int(m.value.rsplit(".", 1)[1])
            for m in cls
            if m.value.rsplit(".", 1)[0] == major_minor
        ]
        return f"{major_minor}.{max(patches)}" if patches else None


class UnsupportedPythonVersionError(Exception):
    def __init__(self, pinned: str):
        super().__init__(
            f"Unsupported Python version {pinned!r} in .python-version. "
            f"Supported versions: {', '.join(SupportedPythonVersion.values())} "
            f"(or a bare {' / '.join(SupportedPythonVersion.major_minors())} "
            f"for the platform default)."
        )


class PythonVersionPin:
    """Parsed ``.python-version`` contents.

    ``full`` is set only when an exact patch release (X.Y.Z) is pinned; a
    bare X.Y or a missing/unparseable file leaves it ``None`` so callers
    fall back to their per-platform defaults.
    """

    major_minor: str | None
    full: str | None

    def __init__(self, major_minor: str | None = None, full: str | None = None):
        self.major_minor = major_minor
        self.full = full

    def full_or(self, default: str) -> str:
        return self.full or default

    def major_minor_or(self, default: str) -> str:
        return self.major_minor or default

    def resolve(self, default: str) -> str:
        """Resolve to an exact version: an explicit X.Y.Z pin wins; a bare
        X.Y pin from a different family than ``default`` resolves to the
        newest supported X.Y.z (so a bare "3.14" builds 3.14.6, not the
        3.13 platform default); otherwise ``default``."""
        if self.full:
            return self.full
        if self.major_minor and not default.startswith(self.major_minor + "."):
            latest = SupportedPythonVersion.latest_for(self.major_minor)
            if latest:
                return latest
        return default


def read_python_version_pin(project_path: Path) -> PythonVersionPin:
    """Read ``<project>/.python-version``; first non-comment line wins.

    Raises ``UnsupportedPythonVersionError`` when the file pins a version
    outside ``SupportedPythonVersion`` (exact pins must be a member; bare
    pins must match a supported major.minor).
    """
    pin_file = Path(project_path) / ".python-version"
    if pin_file.is_file():
        for line in pin_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _PIN_RE.match(line)
            if not m:
                raise UnsupportedPythonVersionError(line)
            major_minor = f"{m[1]}.{m[2]}"
            full = f"{major_minor}.{m[3]}" if m[3] else None
            if full is not None:
                if full not in SupportedPythonVersion:
                    raise UnsupportedPythonVersionError(full)
            elif major_minor not in SupportedPythonVersion.major_minors():
                raise UnsupportedPythonVersionError(major_minor)
            return PythonVersionPin(major_minor, full)
    return PythonVersionPin()
