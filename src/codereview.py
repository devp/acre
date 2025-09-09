#!/usr/bin/env python3
import json
import os
import shlex
import sys
from typing import Dict, Optional

from cli.context import Context as CLI_Context
from cli.parser import parse_args_from_cli
from lib.review_identifier import ReviewIdentifier
from lib.sources.git import get_current_commit_sha, get_repo_root
from lib.state import StateManager


CONFIG_FILE = os.path.expanduser("~/.config/codereview.json")


def load_config():
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as fh:
            json.dump({}, fh)
        return {}
    with open(CONFIG_FILE) as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError:
            return {}


def _rewrite_args_via_aliases(aliases: Optional[Dict]):
    if aliases:
        if len(sys.argv) > 1 and sys.argv[1] in aliases:
            expanded = shlex.split(aliases[sys.argv[1]])
            sys.argv = [sys.argv[0]] + expanded + sys.argv[2:]


def main():
    config = load_config()
    _rewrite_args_via_aliases(config.get("aliases"))
    key = ReviewIdentifier.determine_review_id()
    state_manager = StateManager(
            repo_root=get_repo_root(),
            current_sha=get_current_commit_sha(),
    )
    context = CLI_Context(key=key, state_manager=state_manager, config=config)
    parse_args_from_cli(context=context)

if __name__ == "__main__":
    main()
