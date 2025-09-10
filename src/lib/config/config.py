import os
import tomllib
from typing import Dict

def load_config() -> Dict:
    # TODO: accept an override, either from script and os envs or for tests
    config_path = os.path.expanduser("~/.config/codereview.toml")
    if os.path.exists(config_path):
        with open(config_path, "rb") as fh:
            try:
                return tomllib.load(fh)
            except (tomllib.TOMLDecodeError, FileNotFoundError):
                pass
    return {}
