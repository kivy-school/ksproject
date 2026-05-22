"""Thin wrapper around the Android `emulator` binary."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .adb import ADB, ADBError
from .android_toolchain import DEFAULT_API_VERSION, host_emulator_abi


def _is_alive(pid: int) -> bool:
    """Check if a process is alive using os.kill(pid, 0).
    This works on both POSIX and Windows (Python 3.2+).
    """
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_lock_pid(serial: str) -> int | None:
    """Given an adb serial like 'emulator-5554', return the qemu PID from
    ~/.android/avd/.adb_lock-5554 (emulator writes its PID there)."""
    avd_dir = Path.home() / ".android" / "avd"
    if not avd_dir.is_dir():
        return None
    for lock in avd_dir.glob("*.avd/hardware-qemu.ini.lock"):
        try:
            pid = int(lock.read_text().strip())
        except (OSError, ValueError):
            continue
        if _is_alive(pid):
            return pid  # first live pid — good enough for liveness check
    return None


DEFAULT_AVD_NAME = "ksproject_default"
DEFAULT_AVD_DEVICE = "pixel_xl"


class AndroidEmulatorError(Exception):
    pass


class AndroidEmulator:

    def __init__(self, sdk_path: str, sdk_version: str = str(DEFAULT_API_VERSION)):
        self.sdk_path = sdk_path
        self.sdk_version = sdk_version

        exe_suffix = ".exe" if sys.platform == "win32" else ""
        bat_suffix = ".bat" if sys.platform == "win32" else ""

        self.binary = str(Path(sdk_path) / "emulator" / f"emulator{exe_suffix}")
        self.avdmanager = str(
            Path(sdk_path)
            / "cmdline-tools"
            / "latest"
            / "bin"
            / f"avdmanager{bat_suffix}"
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
            line.strip() for line in (result.stdout or "").splitlines() if line.strip()
        ]

    def ensure_default_avd(self) -> None:
        """Create a default Pixel XL AVD if none exists yet."""
        if not Path(self.binary).exists():
            raise AndroidEmulatorError(f"emulator binary not found at {self.binary}")
        result = subprocess.run(
            [self.binary, "-list-avds"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and (result.stdout or "").strip():
            return  # at least one AVD exists

        abi = host_emulator_abi()
        system_image = f"system-images;android-{self.sdk_version};google_apis;{abi}"
        print(
            f"[ksproject] Creating default AVD '{DEFAULT_AVD_NAME}' "
            f"({DEFAULT_AVD_DEVICE}, {abi})..."
        )
        create = subprocess.run(
            [
                self.avdmanager,
                "create",
                "avd",
                "-n",
                DEFAULT_AVD_NAME,
                "-k",
                system_image,
                "-d",
                DEFAULT_AVD_DEVICE,
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
        kwargs = {}
        if sys.platform == "win32":
            # DETACHED_PROCESS = 0x00000008, CREATE_NEW_PROCESS_GROUP = 0x00000200
            # We use getattr to prevent linting errors on Unix environments
            detached = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            new_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            kwargs["creationflags"] = detached | new_group
        else:
            kwargs["start_new_session"] = True

        env = os.environ.copy()
        env["ANDROID_SDK_ROOT"] = self.sdk_path

        return subprocess.Popen(
            [self.binary, "-avd", name, "-no-snapshot-load"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            env=env,
            **kwargs,
        )

    def _ensure_avd_system_image(self, name: str) -> None:
        """Ensure the AVD points to a system image that actually exists in the SDK.

        If the AVD's config.ini references a system image that isn't installed
        (e.g. android-35), but the project's configured API level (e.g. 36) IS
        installed, update the AVD config to use the available system image
        instead of trying to download old versions.
        """
        avd_dir = Path.home() / ".android" / "avd" / f"{name}.avd"
        avd_ini = avd_dir / "config.ini"
        if not avd_ini.exists():
            return

        abi = host_emulator_abi()
        sdk_root = Path(self.sdk_path)
        system_images_root = sdk_root / "system-images"

        if not system_images_root.exists():
            return

        # Parse the current image.sysdir.1 from config
        try:
            config_text = avd_ini.read_text()
        except OSError:
            return

        current_sysdir = None
        for line in config_text.splitlines():
            if line.startswith("image.sysdir.1"):
                current_sysdir = line.split("=", 1)[1].strip()
                break

        if not current_sysdir:
            return

        # Check if the current system image path exists in our SDK
        if (sdk_root / current_sysdir).exists():
            return  # AVD already points to a valid system image

        # Current system image is missing. Find an available one for the
        # project's configured sdk_version.
        target_sysdir = None
        for api_dir in system_images_root.iterdir():
            if api_dir.is_dir() and api_dir.name.startswith(f"android-{self.sdk_version}"):
                for tag_dir in api_dir.iterdir():
                    if tag_dir.is_dir() and (tag_dir / abi).exists():
                        # Build relative path from SDK root
                        target_sysdir = (
                            f"system-images/{api_dir.name}/{tag_dir.name}/{abi}/"
                        )
                        break
            if target_sysdir:
                break

        if not target_sysdir:
            return

        # Update the AVD config to point to the available system image
        print(
            f"[ksproject] Updating AVD '{name}' to use android-{self.sdk_version} "
            f"system image (was: {current_sysdir.strip('/')})..."
        )
        new_lines = []
        for line in config_text.splitlines():
            if line.startswith("image.sysdir.1"):
                new_lines.append(f"image.sysdir.1={target_sysdir}")
            else:
                new_lines.append(line)
        try:
            avd_ini.write_text("\n".join(new_lines) + "\n")
        except OSError:
            pass

    def boot_and_wait(
        self,
        name: str,
        adb: ADB,
    ) -> str:
        """Boot the named AVD and return the resulting adb serial once online.

        If an emulator running the same AVD is already attached, reuse it.
        Polls until the emulator finishes booting or the qemu process dies —
        no arbitrary timeout.
        """
        already = self._find_running_avd(adb, name)
        if already is not None:
            # Emulator is already up (possibly offline/mid-boot). Wait for it.
            self._wait_for_device(adb, already)
            self._wait_boot_completed(adb, already, proc=None)
            return already

        # Ensure the system image the AVD needs is actually installed.
        self._ensure_avd_system_image(name)

        # No emulator with this AVD visible in adb. Kill any stale qemu that
        # owns the AVD lock so the new launch isn't rejected.
        self._cleanup_stale_lock(name)

        existing = {d["serial"] for d in adb.devices()}
        proc = self.boot(name)

        while True:
            if proc.poll() is not None:
                stderr_output = ""
                stdout_output = ""
                try:
                    stdout_output = (proc.stdout.read() or b"").decode(
                        errors="replace"
                    )
                except Exception:
                    pass
                try:
                    stderr_output = (proc.stderr.read() or b"").decode(
                        errors="replace"
                    )
                except Exception:
                    pass
                detail = "\n".join(
                    filter(None, [stderr_output.strip(), stdout_output.strip()])
                )
                msg = (
                    f"emulator -avd {name} exited with code {proc.returncode} "
                    f"before registering with adb"
                )
                if detail:
                    msg += f"\n\nEmulator output:\n{detail}"
                raise AndroidEmulatorError(msg)
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
                    self._wait_boot_completed(adb, d["serial"], proc=proc)
                    return d["serial"]
            time.sleep(2.0)

    @staticmethod
    def _cleanup_stale_lock(name: str) -> None:
        """Kill any qemu process holding the AVD's hardware-qemu.ini.lock."""
        avd_dir = Path.home() / ".android" / "avd" / f"{name}.avd"
        lock = avd_dir / "hardware-qemu.ini.lock"
        try:
            pid_text = lock.read_text().strip()
        except (OSError, ValueError):
            return
        try:
            pid = int(pid_text)
        except ValueError:
            return

        if not _is_alive(pid):
            # Stale PID — process is gone, but the lockfile remains. Remove
            # it so the emulator doesn't refuse to start.
            try:
                lock.unlink()
            except OSError:
                pass
            return

        # Live process still owns the lock — kill it.
        # Windows doesn't have SIGKILL; SIGTERM forcefully terminates processes.
        sigs = (
            [signal.SIGTERM]
            if sys.platform == "win32"
            else [signal.SIGTERM, signal.SIGKILL]
        )

        for sig in sigs:
            try:
                os.kill(pid, sig)
            except OSError:
                break
            for _ in range(20):
                time.sleep(0.1)
                if not _is_alive(pid):
                    break
            else:
                continue
            break

        try:
            lock.unlink()
        except OSError:
            pass

    @staticmethod
    def _find_running_avd(adb: ADB, name: str) -> str | None:
        """Return the adb serial of an emulator (online or offline) whose AVD
        matches name. Offline serials are returned too so boot_and_wait can
        wait for them to come back online instead of killing and re-launching.
        """
        for d in adb.devices():
            serial = d["serial"]
            if not serial.startswith("emulator-"):
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
    def _wait_for_device(adb: ADB, serial: str) -> None:
        """Wait until an emulator serial is no longer offline."""
        avd_pid = _read_lock_pid(serial)
        while True:
            # If the qemu process for this serial is gone, give up.
            if avd_pid is not None and not _is_alive(avd_pid):
                raise AndroidEmulatorError(
                    f"Emulator process {avd_pid} for {serial} died while waiting for it to come online"
                )
            for d in adb.devices():
                if d["serial"] == serial and d["state"] == "device":
                    return
            time.sleep(2.0)

    @staticmethod
    def _wait_boot_completed(
        adb: ADB,
        serial: str,
        proc: subprocess.Popen | None,
    ) -> None:
        while True:
            if proc is not None and proc.poll() is not None:
                raise AndroidEmulatorError(
                    f"emulator process for {serial} exited with code "
                    f"{proc.returncode} before sys.boot_completed=1"
                )
            try:
                out = adb.shell(serial, "getprop", "sys.boot_completed").strip()
            except ADBError:
                out = ""
            if out == "1":
                return
            time.sleep(2.0)
