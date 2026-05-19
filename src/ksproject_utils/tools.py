import os
import subprocess


def which(name: str) -> str | None:
    result = subprocess.run(
        ["where" if os.name == "nt" else "which", name], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def get_uv() -> str | None:
    return which("uv")
