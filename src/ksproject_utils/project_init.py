"""Initialize a new ksproject (or upgrade an existing uv project).

Ports `PSProject/Sources/PSProject/Init.swift` + `NewToml.swift`.
Drops Swift/iOS/macOS-specific keys; keeps android section.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import toml

from .tools import get_uv


class ProjectInitError(Exception):
    pass


class ProjectInit:

    EXTRA_INDEX_URLS = [
        "https://pypi.anaconda.org/beeware/simple",
        "https://pypi.anaconda.org/pyswift/simple",
        "https://pypi.anaconda.org/kivyschool/simple",
    ]

    def __init__(self, project_path: Path, app_name: str | None = None):
        self.project_path = Path(project_path).resolve()
        self.app_name = app_name or self.project_path.name
        self.module_name = self._resolve_module_name(self.app_name)
        self.pyproject_path = self.project_path / "pyproject.toml"

    @staticmethod
    def _resolve_module_name(name: str) -> str:
        return name.replace("-", "_").replace(".", "_")

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.project_path.mkdir(parents=True, exist_ok=True)

        if not self.pyproject_path.exists():
            self._uv_init()

        if self._already_kivyschool():
            print(f"[ksproject] {self.pyproject_path} already has [tool.kivy-school]; skipping toml updates")
        else:
            self._append_kivyschool_config()

        self._write_app_sources()
        self._ensure_wheelhouse()
        print(f"[ksproject] initialized at {self.project_path}")

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _uv_init(self) -> None:
        uv = get_uv()
        if uv is None:
            raise ProjectInitError(
                "`uv` not found in PATH; install uv to initialize a new project"
            )
        result = subprocess.run(
            [uv, "init", "--name", self.app_name, str(self.project_path)],
        )
        if result.returncode != 0:
            raise ProjectInitError(f"`uv init` exited with code {result.returncode}")

    def _already_kivyschool(self) -> bool:
        with self.pyproject_path.open("r") as f:
            data = toml.load(f)
        tool = data.get("tool", {})
        return "kivy-school" in tool

    def _append_kivyschool_config(self) -> None:
        existing = self.pyproject_path.read_text()
        if not existing.endswith("\n"):
            existing += "\n"

        block = self._kivyschool_block()
        self.pyproject_path.write_text(f"{existing}\n{block}")

    def _kivyschool_block(self) -> str:
        extra_index = ",\n".join(f'    "{u}"' for u in self.EXTRA_INDEX_URLS)
        return f"""\
[tool.uv]
index-strategy = "unsafe-best-match"
find-links = ["./wheelhouse"]

[tool.uv.pip]
extra-index-url = [
{extra_index}
]
find-links = ["./wheelhouse"]

#### kivy-school configuration ####

[tool.kivy-school]
app_name = "{self.app_name}"

[tool.kivy-school.android]
archs = ["arm64-v8a", "x86_64"]
package_name = "org.example.{self.module_name}"
api = 35
min_api = 24
sdk = "35"
ndk = "27.3.13750724"
ndk_api = 24
# sdk_path = "/path/to/android-sdk"
# ndk_path = "/path/to/android-sdk/ndk/27.3.13750724"
# java_path = "/path/to/jdk"
"""

    def _write_app_sources(self) -> None:
        app_src = self.project_path / "src" / self.module_name
        app_src.mkdir(parents=True, exist_ok=True)

        files = {
            "app.py": 'def main():\n    print("Hello World")\n',
            "__init__.py": "from .app import main\n",
            "__main__.py": (
                f"from {self.module_name} import main\n\n"
                'if __name__ == "__main__":\n'
                "    main()\n"
            ),
        }
        for name, content in files.items():
            target = app_src / name
            if not target.exists():
                target.write_text(content)

    def _ensure_wheelhouse(self) -> None:
        (self.project_path / "wheelhouse").mkdir(exist_ok=True)
