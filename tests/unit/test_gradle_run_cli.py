from argparse import Namespace

from ksproject import KSProjectCLI
from ksproject.gradle_commands import GradleCommands
from ksproject_utils.gradle.gradle_project import GradleProjectError
from ksproject_utils.gradle.target_selector import TargetSelectionCancelled


def test_android_run_target_is_optional_for_interactive_selection():
    args = KSProjectCLI().parser.parse_args(["android", "run"])

    assert args.uuid is None
    assert args.name is None
    assert args.variant == "debug"


def test_android_run_still_accepts_explicit_uuid():
    args = KSProjectCLI().parser.parse_args(
        ["android", "run", "--uuid", "emulator-5554"]
    )

    assert args.uuid == "emulator-5554"
    assert args.name is None


def test_android_run_reports_project_errors_without_traceback(monkeypatch, capsys):
    class FailingProject:
        def run(self, **kwargs):
            raise GradleProjectError("Target selection cancelled.")

    monkeypatch.setattr(
        "ksproject.gradle_commands.GradleProject",
        lambda path: FailingProject(),
    )

    result = GradleCommands().run(
        Namespace(uuid=None, name=None, variant="debug")
    )

    assert result == 1
    assert capsys.readouterr().err == "Error: Target selection cancelled.\n"


def test_android_run_reports_cancellation_as_success(monkeypatch, capsys):
    class CancelledProject:
        def run(self, **kwargs):
            raise TargetSelectionCancelled

    monkeypatch.setattr(
        "ksproject.gradle_commands.GradleProject",
        lambda path: CancelledProject(),
    )

    result = GradleCommands().run(
        Namespace(uuid=None, name=None, variant="debug")
    )

    assert result == 0
    assert capsys.readouterr().out == "Cancelled.\n"
