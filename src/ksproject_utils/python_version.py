"""Resolve the app project's pinned Python version from ``.python-version``.

A project may pin an exact patch release (``3.13.11``) — that version then
drives everything: the BeeWare Python-Apple-support build, the CPython
Android build, and every ``uv run --python`` pin in generated build scripts.
A bare major.minor pin (``3.13``) or a missing file means "use ksproject's
built-in defaults" (the versions hardcoded per platform today).
"""
from __future__ import annotations

import re
from pathlib import Path

# Accepts "3.13", "3.13.11" and uv's long form "cpython-3.13.11-macos-...".
_PIN_RE = re.compile(r"^(?:cpython-)?(\d+)\.(\d+)(?:\.(\d+))?")


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


def read_python_version_pin(project_path: Path) -> PythonVersionPin:
    """Read ``<project>/.python-version``; first non-comment line wins."""
    pin_file = Path(project_path) / ".python-version"
    if pin_file.is_file():
        for line in pin_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _PIN_RE.match(line)
            if m:
                major_minor = f"{m[1]}.{m[2]}"
                full = f"{major_minor}.{m[3]}" if m[3] else None
                return PythonVersionPin(major_minor, full)
            break
    return PythonVersionPin()
