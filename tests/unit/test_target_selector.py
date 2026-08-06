from io import StringIO

import pytest

from ksproject_utils.gradle.target_selector import (
    TargetSelectionCancelled,
    TargetSelectionError,
    select_target,
    selectable_targets,
)


TARGETS = [
    {
        "kind": "device",
        "serial": "phone",
        "state": "device",
        "model": "phone model",
    },
    {
        "kind": "device",
        "serial": "offline",
        "state": "offline",
        "model": "offline model",
    },
    {"kind": "avd", "name": "test_avd"},
]


def test_selectable_targets_excludes_unavailable_adb_entries():
    selected = selectable_targets(TARGETS)
    assert [
        item["serial"] if item["kind"] == "device" else item["name"]
        for item in selected
    ] == ["phone", "test_avd"]


def test_select_target_uses_arrow_keys_and_enter():
    keys = iter(("down", "enter"))
    output = StringIO()

    selected = select_target(
        TARGETS,
        output_stream=output,
        key_reader=lambda: next(keys),
    )

    assert selected["name"] == "test_avd"
    assert "phone model (phone)" in output.getvalue()
    assert "test_avd (AVD)" in output.getvalue()


def test_select_target_wraps_when_moving_up_from_first_item():
    keys = iter(("up", "enter"))

    selected = select_target(
        TARGETS,
        key_reader=lambda: next(keys),
    )

    assert selected["name"] == "test_avd"


def test_select_target_auto_selects_the_only_available_target():
    output = StringIO()
    selected = select_target(
        [{"kind": "device", "serial": "phone", "state": "device"}],
        output_stream=output,
        key_reader=lambda: pytest.fail("no key should be read"),
    )

    assert selected["serial"] == "phone"
    assert output.getvalue() == "Using Android target: phone (phone)\n"


def test_select_target_requires_a_terminal_without_an_injected_key_reader():
    with pytest.raises(TargetSelectionError, match="requires a terminal"):
        select_target(TARGETS, input_stream=StringIO())


def test_select_target_reports_when_no_target_is_available():
    with pytest.raises(TargetSelectionError, match="No usable Android targets"):
        select_target([{"kind": "device", "serial": "offline", "state": "offline"}])


def test_select_target_raises_a_distinct_exception_for_cancellation():
    with pytest.raises(TargetSelectionCancelled):
        select_target(TARGETS, key_reader=lambda: "cancel")
