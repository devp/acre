import os
import shlex
import tomllib
from typing import Dict, List, Optional

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

def get_review_test_file_patterns(config: Dict) -> Optional[list[str]]:
    review = config.get("review")
    if not isinstance(review, dict):
        return None
    patterns = review.get("test_file_patterns")
    if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
        return None
    return patterns


def get_review_test_diff_patterns(config: Dict) -> Optional[list[str]]:
    review = config.get("review")
    if not isinstance(review, dict):
        return None
    patterns = review.get("test_diff_patterns")
    if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
        return None
    return patterns


def get_review_test_diff_first_default(config: Dict) -> bool:
    review = config.get("review")
    if not isinstance(review, dict):
        return False
    value = review.get("test_diff_first_default")
    return value is True

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

def get_default_interact_command_for_args(config: Dict) -> Optional[List[str]]:
    """
    Returns a command (as argv tokens) to prepend in interactive mode when the user
    enters only positional args (e.g. "1 2 3"). If unset, returns None.
    """
    raw = config.get("default_interact_command_for_args")
    if not raw:
        return None
    if isinstance(raw, str):
        tokens = shlex.split(raw)
        return tokens if tokens else None
    if isinstance(raw, list):
        return raw if raw else None
    return None
