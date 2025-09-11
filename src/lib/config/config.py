import os
import shlex
import tomllib
from typing import Dict, List

def load_config() -> Dict:
    # TODO: accept an override, either from script and os envs or for tests
    config_path = os.path.expanduser("~/.config/acre.toml")
    if os.path.exists(config_path):
        with open(config_path, "rb") as fh:
            try:
                return tomllib.load(fh)
            except (tomllib.TOMLDecodeError, FileNotFoundError):
                pass
    return {}

def resolve_cmd_from_config_aliases(cmd: str, config: Dict) -> List[str]:
    aliases = config.get("aliases")
    if aliases:
        if cmd in aliases:
            return shlex.split(aliases[cmd])
    return [cmd]

def get_default_commands(config: Dict) -> List[str]:
    default_commands = config.get("default_commands")
    if default_commands:
        if isinstance(default_commands, str):
            return shlex.split(default_commands)
        elif isinstance(default_commands, list):
            return default_commands
    return []
