"""Interactive selection of Android devices and AVDs."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterable
from typing import Any, TextIO


class TargetSelectionError(RuntimeError):
    """Raised when an Android target cannot be selected interactively."""


class TargetSelectionCancelled(TargetSelectionError):
    """Raised when the user intentionally leaves target selection."""


Target = dict[str, Any]
KeyReader = Callable[[], str]


def selectable_targets(items: Iterable[Target]) -> list[Target]:
    """Return targets that can be selected for an immediate run."""

    return [
        item
        for item in items
        if (item.get("kind") == "device" and item.get("state") == "device")
        or item.get("kind") == "avd"
    ]


def target_label(item: Target) -> str:
    """Return a human-readable label for a discovered target."""

    if item.get("kind") == "avd":
        return f"{item.get('name', '<unnamed AVD>')} (AVD)"

    model = item.get("model") or item.get("serial") or "<unnamed device>"
    serial = item.get("serial", "unknown serial")
    return f"{model} ({serial})"


def _read_key_posix(input_stream: TextIO) -> str:
    import termios
    import tty

    try:
        fd = input_stream.fileno()
    except (AttributeError, OSError) as exc:
        raise TargetSelectionError(
            "Interactive target selection requires a terminal. "
            "Use --uuid or --name instead."
        ) from exc

    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        first = input_stream.read(1)
        if first == "\x1b":
            second = input_stream.read(1)
            if second == "[":
                arrow = input_stream.read(1)
                return {"A": "up", "B": "down"}.get(arrow, "unknown")
            return "unknown"
        if first in ("\r", "\n"):
            return "enter"
        if first == "\x03":
            return "cancel"
        if first.lower() == "q":
            return "cancel"
        return "unknown"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _read_key_windows() -> str:
    import msvcrt

    key = msvcrt.getwch()
    if key in ("\x00", "\xe0"):
        return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "unknown")
    if key == "\r":
        return "enter"
    if key == "\x03" or key.lower() == "q":
        return "cancel"
    return "unknown"


def read_key(input_stream: TextIO = sys.stdin) -> str:
    """Read one navigation key from the terminal."""

    if os.name == "nt":
        return _read_key_windows()
    return _read_key_posix(input_stream)


def _render(
    candidates: list[Target],
    selected: int,
    output_stream: TextIO,
    redraw: bool,
) -> None:
    if redraw:
        output_stream.write(f"\033[{len(candidates)}A")

    for index, item in enumerate(candidates):
        marker = "❯" if index == selected else " "
        output_stream.write(f"\r\033[2K{marker} {target_label(item)}\n")
    output_stream.flush()


def select_target(
    items: Iterable[Target],
    *,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    key_reader: KeyReader | None = None,
) -> Target:
    """Select an Android target with the arrow keys and Enter.

    A single available target is selected automatically. ``key_reader`` is
    injectable so this behavior can be tested without a real terminal.
    """

    candidates = selectable_targets(items)
    if not candidates:
        raise TargetSelectionError(
            "No usable Android targets were found. Connect a device, start an "
            "emulator, or use --uuid/--name."
        )
    if len(candidates) == 1:
        output_stream.write(f"Using Android target: {target_label(candidates[0])}\n")
        output_stream.flush()
        return candidates[0]

    if key_reader is None:
        if not input_stream.isatty():
            raise TargetSelectionError(
                "Interactive target selection requires a terminal. "
                "Use --uuid or --name instead."
            )
        key_reader = lambda: read_key(input_stream)

    output_stream.write("Select an Android target (↑/↓, Enter; q cancels):\n")
    _render(candidates, 0, output_stream, redraw=False)
    selected = 0

    while True:
        try:
            key = key_reader()
        except KeyboardInterrupt as exc:
            raise TargetSelectionCancelled from exc

        if key == "up":
            selected = (selected - 1) % len(candidates)
            _render(candidates, selected, output_stream, redraw=True)
        elif key == "down":
            selected = (selected + 1) % len(candidates)
            _render(candidates, selected, output_stream, redraw=True)
        elif key == "enter":
            return candidates[selected]
        elif key == "cancel":
            raise TargetSelectionCancelled
