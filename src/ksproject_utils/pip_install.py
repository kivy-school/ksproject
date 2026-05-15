from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path

from .platforms import Platform
from .tools import get_uv

UV = get_uv()


class PipInstallError(Exception):
    pass


class PipInstaller:
    @staticmethod
    def install(uv_src: str, platform: Platform, site_packages: str) -> None:
        project_dir = Path(uv_src).resolve()

        try:
            subprocess.check_call([
                UV, "pip", "install", uv_src,
                "--python-platform", platform.pip_platform,
                "--index-strategy", "unsafe-best-match",
                "--target", site_packages,
            ])
        except subprocess.CalledProcessError as e:
            raise PipInstallError(f"Failed to install '{uv_src}': {e}")

        # Copy .java / .libs / .kotlin from local dep source trees into site_packages.
        # These dot-directories are not included in wheels, so ksproject collects them.
        sp = Path(site_packages)
        for local_path in _collect_local_paths(project_dir):
            for dot_dir in (".java", ".libs", ".kotlin"):
                src = local_path / dot_dir
                if src.is_dir():
                    shutil.copytree(src, sp / dot_dir, dirs_exist_ok=True)


def _collect_local_paths(project_dir: Path, visited: set[Path] | None = None) -> list[Path]:
    """Recursively collect all local path and workspace dependency directories."""
    if visited is None:
        visited = set()

    project_dir = project_dir.resolve()
    if project_dir in visited:
        return []
    visited.add(project_dir)

    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return []

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    uv_cfg = data.get("tool", {}).get("uv", {})
    sources: dict = uv_cfg.get("sources", {})
    workspace_patterns: list[str] = uv_cfg.get("workspace", {}).get("members", [])

    # Build package-name → path map for workspace members declared in this project.
    workspace_map: dict[str, Path] = {}
    for pattern in workspace_patterns:
        for member_dir in project_dir.glob(pattern):
            member_pyproject = member_dir / "pyproject.toml"
            if not member_pyproject.exists():
                continue
            with member_pyproject.open("rb") as f:
                member_data = tomllib.load(f)
            name = member_data.get("project", {}).get("name", "")
            if name:
                workspace_map[_normalize(name)] = member_dir.resolve()

    result: list[Path] = []
    for pkg_name, source in sources.items():
        if "path" in source:
            local_path = (project_dir / source["path"]).resolve()
            result.append(local_path)
            result.extend(_collect_local_paths(local_path, visited))
        elif source.get("workspace"):
            member_path = workspace_map.get(_normalize(pkg_name))
            if member_path:
                result.append(member_path)
                result.extend(_collect_local_paths(member_path, visited))

    return result


def _normalize(name: str) -> str:
    return name.lower().replace("-", "_").replace(".", "_")