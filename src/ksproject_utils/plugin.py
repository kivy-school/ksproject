
import argparse
import importlib
from typing import Protocol
import toml
from pathlib import Path

class CommandPlugin(Protocol):
    def register(self, subparsers: argparse._SubParsersAction) -> None:
        ...


def load_plugins() -> list[CommandPlugin]:
    results: list[CommandPlugin] = []
    plugin_list: list[str] = []
    toml_path = Path.cwd() / "ksproject.toml"
    if toml_path.exists():
        with open(toml_path) as f:
            plugins_toml = toml.load(f)
            plugin_list = plugins_toml.get("command_plugins", [])

    for module_name in plugin_list:
        module = importlib.import_module(module_name)
        results.append(module.plugin)

    return results