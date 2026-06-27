import os
import subprocess
import re

def which(name: str) -> str | None:
    result = subprocess.run(
        ["where" if os.name == "nt" else "which", name], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None

    output = result.stdout.strip()
    if not output:
        return None

    return output.splitlines()[0].strip()


def get_uv() -> str | None:
    return which("uv")


def load_dotenv(file_path=".env"):
    """
    Loads environment variables from a .env file into os.environ.
    """
    try:
        with open(file_path, "r") as file:
            for line in file:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)

                    key = key.strip()
                    value = value.strip()

                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]

                    os.environ[key] = value

        print(f"Successfully loaded environment variables from '{file_path}'.")

    except FileNotFoundError:
        print(f"Info: '{file_path}' file not found. Skipping.")
    except Exception as e:
        print(f"Error loading '{file_path}': {e}")


REPLACE_CHARS = [
    "-",
    ".",
    " "
] 

RESOLVE_REGEX = fr"[{"".join(REPLACE_CHARS)}]"

def resolve_module_name(name: str) -> str:
    return re.sub(RESOLVE_REGEX, "_", name).lower().strip()