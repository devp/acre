#!/usr/bin/env python3
import json
import os
import re
import shlex
import subprocess
import sys

from lib.cli import CommandOptions, Commands, parse_args_from_cli, print_usage
from lib.initialize import cmd_init
from lib.review_identifier import ReviewIdentifier
from lib.sources.git import get_current_commit_sha, get_repo_root
from lib.sources.github import data_from_gh
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

def yn(prompt, default=False):
    ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    if not ans:
        return default
    return ans == "y"


def run_review_cmd(path):
    config = load_config()
    cmd = config.get("actions", {}).get("onReview")
    if cmd:
        if "{file}" in cmd:
            cmd = cmd.replace("{file}", shlex.quote(path))
            args = shlex.split(cmd)
        else:
            args = shlex.split(cmd) + [path]
    else:
        args = ["git", "diff", "main", "--", path]
    subprocess.run(args)


def find_jira(text):
    m = re.search(r"[A-Z][A-Z0-9]+-\d+", text or "")
    return m.group(0) if m else None


class CommandsV0:
    def __init__(self, state_manager: StateManager, key: str):
        self.key = key
        self.state_manager = state_manager
        _state = self.state_manager.load_state(key)
        if not _state:
            raise Exception("No state file: run init first")
        self.state = _state

    def cmd_overview(self, config):
        data = data_from_gh()
        title = data.title or ""
        body = data.body or ""
        files = data.files
        print(f"\U0001F4CC PR Summary: {title}")
        jira = find_jira("\n".join([title, body]))
        jira_base = config.get("jira", {}).get("base")
        if jira and jira_base:
            print(f"\U0001F517 Jira: https://{jira_base}.atlassian.net/browse/{jira}")
        elif jira:
            print(f"\U0001F517 Jira: {jira}")
        if body:
            print(f"> {body}")
        changed_lines_total = 0
        print("\n\U0001F4C1 File Summary:")
        for idx, path in enumerate(files, 1):
            reviewed = self.state.is_file_reviewed(path)
            lines = data.lines_changed.get(path, 0)
            changed_lines_total += lines
            mark = "\u2705 " if reviewed else ""
            print(f"{idx}. {mark}{path:25} +{lines}")
        print(f"\n\U0001F9AE Total: {len(files)} files, {changed_lines_total} changed lines")


    def cmd_status(self):
        total = self.state.total_lines()
        reviewed = self.state.total_reviewed_lines()
        remaining = total - reviewed
        pct = int((reviewed / total) * 100) if total else (100 if reviewed else 0)
        num_files = len(self.state.files)
        num_files_reviewed = len(self.state.reviewed_files())
        files_left = num_files - num_files_reviewed
        print(f"> {remaining} lines remaining | {pct}% reviewed | {files_left} files touched")


    def cmd_review(self, path, mode):
        if not self.state or path not in self.state["files"]:
            print("Unknown file. Run 'codereview overview' first.")
            return False
        if self.state.is_file_reviewed(path):
            print(f"{path} already reviewed")
            return False
        run_review_cmd(path)
        if not yn("Mark reviewed?"):
            return False
        self.state_manager.mark_file_reviewed(self.state, path)
        self.state_manager.save_state(self.state)
        lines = self.state.lines_of_file(path)
        print(f"> Marked {lines} lines as reviewed ({mode} mode)")
        return True


    def cmd_reset(self):
        self.state_manager.do_reset(self.state)
        self.state_manager.save_state(self.state)


def main():
    config = load_config()
    aliases = config.get("aliases", {})
    if len(sys.argv) > 1 and sys.argv[1] in aliases:
        expanded = shlex.split(aliases[sys.argv[1]])
        sys.argv = [sys.argv[0]] + expanded + sys.argv[2:]

    state_manager = StateManager(
            repo_root=get_repo_root(),
            current_sha=get_current_commit_sha(),
    )
    key = ReviewIdentifier.determine_review_id()
    cmd_v0 = CommandsV0(state_manager, key)

    instruction = parse_args_from_cli()
    if instruction:
        match instruction.command:
            case Commands.INIT:
                is_force = CommandOptions.INIT_FORCE in instruction.options
                return cmd_init(state_manager=state_manager, review_id=instruction.reviewId, force=is_force)
            case Commands.OVERVIEW:
                return cmd_v0.cmd_overview(config=config)
            case Commands.STATUS:
                return cmd_v0.cmd_status()
            case Commands.RESET:
                return cmd_v0.cmd_reset()
            case Commands.REVIEW:
                mode = "deep" if CommandOptions.REVIEW_DEEP in instruction.options else "skim"
                return cmd_v0.cmd_review(path=instruction.filePath, mode=mode)
    print_usage()


if __name__ == "__main__":
    main()
