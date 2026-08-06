from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from ksproject_utils.gradle.adb import ADB, ADBError
from ksproject_utils.gradle.gradle_project import GradleProject, GradleProjectError
from ksproject.gradle_commands import GradleCommands


def test_install_prints_successful_adb_output(monkeypatch, capsys):
    adb = ADB("/android-sdk")

    def fake_run(*args, **kwargs):
        assert args == ("-s", "serial", "install", "-r", "app.apk")
        assert kwargs == {}
        return SimpleNamespace(stdout="Performing Streamed Install\nSuccess\n")

    monkeypatch.setattr(adb, "_run", fake_run)

    adb.install(Path("app.apk"), "serial")

    assert capsys.readouterr().out == "Performing Streamed Install\nSuccess\n"


def test_version_downgrade_has_an_actionable_message(monkeypatch):
    class FailingADB:
        binary = "/android-sdk/platform-tools/adb"

        def wait_for_device(self, serial):
            pass

        def install(self, apk, serial):
            raise ADBError(
                "adb -s serial install -r app.apk failed: "
                "adb: failed to install app.apk: "
                "Failure [INSTALL_FAILED_VERSION_DOWNGRADE: "
                "Update version code 2 is older than current 1024200]"
            )

    project = object.__new__(GradleProject)
    project.adb = FailingADB()
    project.emulator = object()
    project.android_data = SimpleNamespace(package_name="org.example.app")
    monkeypatch.setattr(project, "find_apk", lambda variant: Path("app.apk"))

    with pytest.raises(GradleProjectError) as error:
        project.run(uuid="serial")

    message = str(error.value)
    assert "lower Android version code" in message
    assert "already installed on serial" in message
    assert "adb -s serial uninstall org.example.app" in message


def test_android_run_reports_adb_errors_without_a_traceback(monkeypatch, capsys):
    class FailingProject:
        def run(self, **kwargs):
            raise ADBError("adb install failed: device offline")

    monkeypatch.setattr(
        "ksproject.gradle_commands.GradleProject",
        lambda path: FailingProject(),
    )

    result = GradleCommands().run(
        Namespace(uuid="serial", name=None, variant="debug")
    )

    assert result == 1
    assert capsys.readouterr().err == "Error: adb install failed: device offline\n"
