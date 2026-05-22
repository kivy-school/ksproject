"""Collect and merge .gradle/*.json configs from installed site-packages.

When packages are built with ``ksp-builder``, they include a
``.gradle/<package_name>.json`` file declaring extra ``gradle_dependencies``
and ``permissions`` needed by that package.  This module scans the
site-packages tree, parses all such JSON files, and returns de-duplicated
merged lists that ksproject can feed into the Gradle project generation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MergedGradleConfig:
    """Aggregated gradle dependencies and permissions from all packages."""

    gradle_dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


def collect_gradle_json_files(site_packages_dir: Path) -> list[Path]:
    """Return all ``.gradle/*.json`` files found under *site_packages_dir*."""
    gradle_dir = site_packages_dir / ".gradle"
    if not gradle_dir.is_dir():
        return []
    return sorted(gradle_dir.glob("*.json"))


def parse_gradle_json(path: Path) -> tuple[list[str], list[str]]:
    """Parse a single ksp-builder JSON file.

    Returns (gradle_dependencies, permissions).
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return (
        data.get("gradle_dependencies", []),
        data.get("permissions", []),
    )


def collect_and_merge(site_packages_dirs: list[Path]) -> MergedGradleConfig:
    """Scan multiple site-packages directories and merge all gradle configs.

    Parameters
    ----------
    site_packages_dirs:
        List of per-ABI site_packages directories to scan (e.g.
        ``[<project>/site_packages/arm64-v8a, <project>/site_packages/x86_64]``).
        Since all ABIs get the same pure-Python packages the ``.gradle/``
        content is identical across ABIs — we scan all to be safe but
        deduplicate the results.

    Returns
    -------
    MergedGradleConfig with deduplicated gradle_dependencies and permissions.
    """
    deps_seen: dict[str, None] = {}  # insertion-ordered set preserving discovery order
    perms_seen: dict[str, None] = {}

    for sp_dir in site_packages_dirs:
        for json_path in collect_gradle_json_files(sp_dir):
            deps, perms = parse_gradle_json(json_path)
            for d in deps:
                deps_seen.setdefault(d, None)
            for p in perms:
                perms_seen.setdefault(p, None)

    return MergedGradleConfig(
        gradle_dependencies=list(deps_seen.keys()),
        permissions=list(perms_seen.keys()),
    )
