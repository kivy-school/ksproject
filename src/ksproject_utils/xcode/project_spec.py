"""Build the top-level XcodeGen project spec dict.

Ports ``PSProject/Sources/XcodeProjectBuilder/Project/Project.swift``.
"""

from __future__ import annotations

from typing import Any

from . import setting_presets as sp
from .project_target import ProjectTarget


class ProjectSpec:
    """Builds the full XcodeGen ``project.yml`` dictionary."""

    def __init__(
        self,
        name: str,
        bundle_id_prefix: str,
        target: ProjectTarget,
    ) -> None:
        self.name = name
        self.bundle_id_prefix = bundle_id_prefix
        self.target = target

    def _configs(self) -> dict[str, str]:
        return {"Debug": "debug", "Release": "release"}

    def _project_settings(self) -> dict[str, Any]:
        return {
            "configs": {
                "Debug": sp.project_settings("debug"),
                "Release": sp.project_settings("release"),
            }
        }

    def _packages(self) -> dict[str, dict[str, Any]]:
        return {
            "CPython": {
                "url": "https://github.com/py-swift/CPython",
                "from": "313.0.0",
            },
            "PySwiftKit": {
                "url": "https://github.com/py-swift/PySwiftKit",
                "from": "313.0.0",
            },
            "KivyLauncher": {
                "url": "https://github.com/kivy-school/KivyLauncher",
                "branch": "master",
            },
            "Kivy_iOS_Module": {
                "url": "https://github.com/kivy-school/Kivy_iOS_Module",
                "branch": "master",
            },
        }

    def _options(self) -> dict[str, Any]:
        return {
            "bundleIdPrefix": self.bundle_id_prefix,
            "settingPresets": "none",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "options": self._options(),
            "configs": self._configs(),
            "settings": self._project_settings(),
            "packages": self._packages(),
            "targets": {self.name: self.target.to_dict()},
        }
