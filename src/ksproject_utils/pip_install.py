from .platforms import (
    Platform,
)
from .tools import get_uv
import subprocess

UV = get_uv()

class PipInstallError(Exception):
    """Custom exception for pip installation errors."""
    pass


class PipInstaller:
    """Class to handle pip installations."""

    @staticmethod
    def install(uv_src: str, platform: Platform, site_packages: str):
        """Install a package using pip."""
        
        pip_args = [
            "--python-platform", platform.pip_platform,
            #"--python-version", "3.13",
            "--index-strategy", "unsafe-best-match",
            "--target", site_packages
        ]
        try:
            subprocess.check_call([UV, "pip", "install", uv_src, *pip_args])
        except subprocess.CalledProcessError as e:
            raise PipInstallError(f"Failed to install '{uv_src}': {e}")