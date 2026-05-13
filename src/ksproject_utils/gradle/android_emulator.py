"""Thin wrapper around the Android `emulator` binary."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .adb import ADB, ADBError
from .android_toolchain import host_emulator_abi


DEFAULT_AVD_NAME = "ksproject_default"
DEFAULT_AVD_DEVICE = "pixel_xl"


class AndroidEmulatorError(Exception):
    pass


class AndroidEmulator:

    def __init__(self, sdk_path: str, sdk_version: str = "35"):
        self.sdk_path = sdk_path
        self.sdk_version = sdk_version
        self.binary = str(Path(sdk_path) / "emulator" / "emulator")
        self.avdmanager = str(
            Path(sdk_path) / "cmdline-tools" / "latest" / "bin" / "avdmanager"
        )

    def list_avds(self) -> list[str]:
        self.ensure_default_avd()
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

    def ensure_default_avd(self) -> None:
        """Create a default Pixel XL AVD if none exists yet."""
        if not Path(self.binary).exists():
            raise AndroidEmulatorError(
                f"emulator binary not found at {self.binary}"
            )
        result = subprocess.run(
            [self.binary, "-list-avds"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and (result.stdout or "").strip():
            return  # at least one AVD exists

        abi = host_emulator_abi()
        system_image = (
            f"system-images;android-{self.sdk_version};google_apis;{abi}"
        )
        print(
            f"[ksproject] Creating default AVD '{DEFAULT_AVD_NAME}' "
            f"({DEFAULT_AVD_DEVICE}, {abi})..."
        )
        create = subprocess.run(
            [
                self.avdmanager,
                "create",
                "avd",
                "-n", DEFAULT_AVD_NAME,
                "-k", system_image,
                "-d", DEFAULT_AVD_DEVICE,
                "-f",
            ],
            input="no\n",
            capture_output=True,
            text=True,
        )
        if create.returncode != 0:
            raise AndroidEmulatorError(
                f"avdmanager create avd failed: "
                f"{(create.stderr or create.stdout or '').strip()}"
            )

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
        """Boot the named AVD and return the resulting adb serial once online.

        If an emulator running the same AVD is already attached, reuse it.
        """
        already = self._find_running_avd(adb, name)
        if already is not None:
            self._wait_boot_completed(adb, already, time.monotonic() + timeout)
            return already

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
    def _find_running_avd(adb: ADB, name: str) -> str | None:
        """Return the adb serial of a running emulator whose AVD matches name."""
        for d in adb.devices():
            serial = d["serial"]
            if not serial.startswith("emulator-") or d["state"] != "device":
                continue
            try:
                result = subprocess.run(
                    [adb.binary, "-s", serial, "emu", "avd", "name"],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                )
            except (subprocess.TimeoutExpired, OSError):
                continue
            if result.returncode != 0:
                continue
            first_line = (result.stdout or "").splitlines()[:1]
            if first_line and first_line[0].strip() == name:
                return serial
        return None

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
