"""Thin wrapper around the Android `adb` binary."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path


class ADBError(Exception):
    pass


class ADB:

    def __init__(self, sdk_path: str):
        self.sdk_path = sdk_path
        self.binary = str(Path(sdk_path) / "platform-tools" / "adb")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(self, *args: str, capture: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [self.binary, *args],
            capture_output=capture,
            text=True,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise ADBError(f"adb {' '.join(args)} failed: {stderr}")
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def devices(self) -> list[dict]:
        """Return all connected devices/emulators as dicts.

        Each dict has at least: serial, state, model, transport_id.
        """
        result = self._run("devices", "-l")
        out = result.stdout or ""
        devices: list[dict] = []
        for line in out.splitlines()[1:]:  # skip "List of devices attached"
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else "unknown"
            extras: dict[str, str] = {}
            for p in parts[2:]:
                if ":" in p:
                    k, _, v = p.partition(":")
                    extras[k] = v
            devices.append({
                "serial": serial,
                "state": state,
                "model": extras.get("model", ""),
                "transport_id": extras.get("transport_id", ""),
                "kind": "device",
            })
        return devices

    def install(self, apk: Path, serial: str, replace: bool = True) -> None:
        args = ["-s", serial, "install"]
        if replace:
            args.append("-r")
        args.append(str(apk))
        self._run(*args, capture=False)

    def shell(self, serial: str, *args: str) -> str:
        result = self._run("-s", serial, "shell", *args)
        return result.stdout or ""

    def start_app(
        self,
        serial: str,
        package: str,
        activity: str = ".MainActivity",
    ) -> None:
        component = f"{package}/{activity}"
        self.shell(serial, "am", "start", "-n", component)

    def wait_for_device(self, serial: str, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for d in self.devices():
                if d["serial"] == serial and d["state"] == "device":
                    return
            time.sleep(1.0)
        raise ADBError(f"Timed out waiting for device {serial}")
