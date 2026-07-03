"""Initialize a new ksproject (or upgrade an existing uv project).

Ports `PSProject/Sources/PSProject/Init.swift` + `NewToml.swift`.
Drops Swift/iOS/macOS-specific keys; keeps android section.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import toml

from .tools import get_uv

from .templates.base_app import app_kv, app_py

from .pyproject_init import PyProjectInitKeys

from .gradle.project_init import GradleProjectInit


class ProjectInitError(Exception):
    pass


class ProjectInit:

    EXTRA_INDEX_URLS = [
        # "https://pypi.anaconda.org/beeware/simple",
        #"https://pypi.anaconda.org/pyswift/simple",
        "https://pypi-index.psychowaspx.workers.dev/simple/",
        "https://pypi.anaconda.org/kivyschool/simple",
    ]

    def __init__(self, project_path: Path, app_name: str | None = None):
        self.project_path = Path(project_path).resolve()
        self.app_name = app_name or self.project_path.name
        self.module_name = self._resolve_module_name(self.app_name)
        self.pyproject_path = self.project_path / "pyproject.toml"

    @staticmethod
    def _resolve_module_name(name: str) -> str:
        return name.lower().replace("-", "_").replace(".", "_")

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.project_path.mkdir(parents=True, exist_ok=True)

        if not self.pyproject_path.exists():
            self._uv_init()

        if self._already_kivyschool():
            print(
                f"[ksproject] {self.pyproject_path} already has [tool.kivy-school]; skipping toml updates"
            )
        else:
            self._append_kivyschool_config()

        self._write_app_sources()
        self._ensure_wheelhouse()
        # self._ensure_base_dirs()
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

        block = PyProjectInitKeys(self.app_name).output()
        self.pyproject_path.write_text(f"{existing}\n{block}")

    def _write_app_sources(self) -> None:
        app_src = self.project_path / "src" / self.module_name
        app_src.mkdir(parents=True, exist_ok=True)

        init_py_content = f"""\
def main(*args) -> None:
    from .app import main
    main()
"""

        main_py_content = """\
from .app import main

if __name__ == "__main__":
    main()
"""

        gitignore_content = """\
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[codz]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#   Usually these files are written by a python script from a template
#   before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py.cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
#   For a library or package, you might want to ignore these files since the code is
#   intended to run in multiple environments; otherwise, check them in:
# .python-version

# pipenv
#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.
#   However, in case of collaboration, if having platform-specific dependencies or dependencies
#   having no cross-platform support, pipenv may install dependencies that don't work, or not
#   install all needed dependencies.
# Pipfile.lock

# UV
#   Similar to Pipfile.lock, it is generally recommended to include uv.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
# uv.lock

# poetry
#   Similar to Pipfile.lock, it is generally recommended to include poetry.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
#   https://python-poetry.org/docs/basic-usage/#commit-your-poetrylock-file-to-version-control
# poetry.lock
# poetry.toml

# pdm
#   Similar to Pipfile.lock, it is generally recommended to include pdm.lock in version control.
#   pdm recommends including project-wide configuration in pdm.toml, but excluding .pdm-python.
#   https://pdm-project.org/en/latest/usage/project/#working-with-version-control
# pdm.lock
# pdm.toml
.pdm-python
.pdm-build/

# pixi
#   Similar to Pipfile.lock, it is generally recommended to include pixi.lock in version control.
# pixi.lock
#   Pixi creates a virtual environment in the .pixi directory, just like venv module creates one
#   in the .venv directory. It is recommended not to include this directory in version control.
.pixi

# PEP 582; used by e.g. github.com/David-OConnor/pyflow and github.com/pdm-project/pdm
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# Redis
*.rdb
*.aof
*.pid

# RabbitMQ
mnesia/
rabbitmq/
rabbitmq-data/

# ActiveMQ
activemq-data/

# SageMath parsed files
*.sage.py

# Environments
.env
.envrc
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
#   JetBrains specific template is maintained in a separate JetBrains.gitignore that can
#   be found at https://github.com/github/gitignore/blob/main/Global/JetBrains.gitignore
#   and can be added to the global gitignore or merged into this file.  For a more nuclear
#   option (not recommended) you can uncomment the following to ignore the entire idea folder.
# .idea/

# Abstra
#   Abstra is an AI-powered process automation framework.
#   Ignore directories containing user credentials, local state, and settings.
#   Learn more at https://abstra.io/docs
.abstra/

# Visual Studio Code
#   Visual Studio Code specific template is maintained in a separate VisualStudioCode.gitignore 
#   that can be found at https://github.com/github/gitignore/blob/main/Global/VisualStudioCode.gitignore
#   and can be added to the global gitignore or merged into this file. However, if you prefer, 
#   you could uncomment the following to ignore the entire vscode folder
# .vscode/
# Temporary file for partial code execution
tempCodeRunnerFile.py

# Ruff stuff:
.ruff_cache/

# PyPI configuration file
.pypirc

# Marimo
marimo/_static/
marimo/_lsp/
__marimo__/

# Streamlit
.streamlit/secrets.toml
.DS_Store



# Python
uv.lock
.build-target

# kivyschool
project_dist/
.kivyschool
# wheelhouse/

# Java keystores
*.jks

# Android
google-services.json
"""

        env_content = """\
# ONESIGNAL_APP_ID=""
# KEYSTORE=""
# KEYALIAS=""
# STOREPASS=""
# KEYPASS="defaults_to_storepass"
"""

        # --- File Assignment Map ---
        files = {
            "app.py": app_py,
            "app.kv": app_kv,
            "__init__.py": init_py_content,
            "__main__.py": main_py_content,
        }

        # --- Target Write Loop ---
        for name, content in files.items():
            target = app_src / name
            target.write_text(content, encoding="utf-8")

        (self.project_path / ".gitignore").write_text(gitignore_content, encoding="utf-8")

        (self.project_path / ".env").write_text(env_content, encoding="utf-8")

        GradleProjectInit(self.project_path, self.module_name).execute()

    def _ensure_wheelhouse(self) -> None:
        wheelhouse = (self.project_path / "wheelhouse")
        wheelhouse.mkdir(exist_ok=True)
        (wheelhouse / ".gitkeep").touch()