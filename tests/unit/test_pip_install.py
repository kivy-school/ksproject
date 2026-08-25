from pathlib import Path

from ksproject_utils.pip_install import (
    PipInstaller,
    collect_local_package_names,
)


def _write_pyproject(path: Path, name: str, source: str | None = None) -> None:
    sources = f'\n[tool.uv.sources]\n{name} = {{ path = "{source}" }}\n' if source else ''
    (path / 'pyproject.toml').write_text(
        f'[project]\nname = "{name}"\nversion = "0.1.0"\n{sources}',
        encoding='utf-8',
    )


def test_collect_local_package_names_includes_root_and_path_dependencies(tmp_path):
    dependency = tmp_path / 'dependency'
    dependency.mkdir()
    _write_pyproject(dependency, 'local-dependency')
    _write_pyproject(tmp_path, 'root-project', 'dependency')

    assert collect_local_package_names(tmp_path) == [
        'root-project',
        'local-dependency',
    ]


def test_install_reinstalls_local_packages(monkeypatch, tmp_path):
    _write_pyproject(tmp_path, 'root-project')
    calls = []
    monkeypatch.setattr(
        'ksproject_utils.pip_install.subprocess.check_call',
        calls.append,
    )
    monkeypatch.setattr('ksproject_utils.pip_install.UV', 'uv')

    class Platform:
        pip_platform = 'aarch64-linux-android'

    PipInstaller.install(str(tmp_path), Platform(), str(tmp_path / 'target'))

    command = calls[0]
    assert command[-2:] == ['--reinstall-package', 'root-project']
