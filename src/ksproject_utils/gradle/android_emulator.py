"""Thin wrapper around the Android `emulator` binary."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .adb import ADB, ADBError


class AndroidEmulatorError(Exception):
    pass


class AndroidEmulator:

    def __init__(self, sdk_path: str):
        self.sdk_path = sdk_path
        self.binary = str(Path(sdk_path) / "emulator" / "emulator")

    def list_avds(self) -> list[str]:
        result = subprocess.run(
            [self.binary, "-list-avds"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AndroidEmulatorError(
                f"emulator -list-avds failed: {(result.stderr or '').strip()}"
            )
        return [
            line.strip()
            for line in (result.stdout or "").splitlines()
            if line.strip()
        ]

    def boot(self, name: str) -> subprocess.Popen:
        """Spawn `emulator -avd <name>` detached and return the Popen handle."""
        return subprocess.Popen(
            [self.binary, "-avd", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    def boot_and_wait(
        self,
        name: str,
        adb: ADB,
        timeout: float = 120.0,
    ) -> str:
        """Boot the named AVD and return the resulting adb serial once online."""
        existing = {d["serial"] for d in adb.devices()}
        self.boot(name)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                current = adb.devices()
            except ADBError:
                current = []
            for d in current:
                if (
                    d["serial"].startswith("emulator-")
                    and d["serial"] not in existing
                    and d["state"] == "device"
                ):
                    # Wait for boot completion
                    self._wait_boot_completed(adb, d["serial"], deadline)
                    return d["serial"]
            time.sleep(2.0)
        raise AndroidEmulatorError(f"Timed out booting AVD '{name}'")

    @staticmethod
    def _wait_boot_completed(adb: ADB, serial: str, deadline: float) -> None:
        while time.monotonic() < deadline:
            try:
                out = adb.shell(serial, "getprop", "sys.boot_completed").strip()
            except ADBError:
                out = ""
            if out == "1":
                return
            time.sleep(2.0)
        raise AndroidEmulatorError(
            f"Emulator {serial} did not finish booting in time"
        )
