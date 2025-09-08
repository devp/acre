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
from lib.state import StateManager


def repo_root():
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return os.getcwd()

CONFIG_FILE = os.path.expanduser("~/.config/codereview.json")


def current_key():
    return ReviewIdentifier.determine_review_id()


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


def load_state(key):
    state = StateManager().load_state(key)
    if not state:
        print("No state file: run init first")
        exit(1)
    return state


def save_state(state):
    StateManager().save_state(state)


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


def gh_view():
    try:
        res = subprocess.run(
            ["gh", "pr", "view", "--json", "title,body,files"],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(res.stdout)
    except subprocess.CalledProcessError:
        print("gh pr view failed; ensure you're on a PR branch")
        print("TODO: make this robust for other branches and other info sources")
        sys.exit(1)


def find_jira(text):
    m = re.search(r"[A-Z][A-Z0-9]+-\d+", text or "")
    return m.group(0) if m else None


def cmd_overview(config, interactive=False):
    key = current_key()
    data = gh_view() or {}
    title = data.get("title", "").strip()
    body = data.get("body", "").strip() or ""
    print(f"\U0001F4CC PR Summary: {title}")
    jira = find_jira("\n".join([title, body]))
    jira_base = config.get("jira", {}).get("base")
    if jira and jira_base:
        print(f"\U0001F517 Jira: https://{jira_base}.atlassian.net/browse/{jira}")
    elif jira:
        print(f"\U0001F517 Jira: {jira}")
    if body:
        print(f"> {body}")
    files = data.get("files", [])
    changed_lines_total = 0
    state = load_state(key)
    print("\n\U0001F4C1 File Summary:")
    paths = []
    for idx, f in enumerate(files, 1):
        path = f.get("path")
        lines = f.get("additions", 0) + f.get("deletions", 0)
        reviewed = state.is_file_reviewed(path)
        changed_lines_total += lines
        paths.append(path)
        mark = "\u2705 " if reviewed else ""
        if interactive:
            print(f"{idx}. {mark}{path:25} +{lines}")
        else:
            print(f"- {mark}{path:25} +{lines}")
    print(f"\n\U0001F9AE Total: {len(files)} files, {changed_lines_total} changed lines")
    if interactive:
        _interactive_session(paths, key)


def cmd_status():
    key = current_key()
    state = load_state(key)
    total = state.total_lines()
    reviewed = state.total_reviewed_lines()
    remaining = total - reviewed
    pct = int((reviewed / total) * 100) if total else (100 if reviewed else 0)
    num_files = len(state.files)
    num_files_reviewed = len(state.reviewed_files())
    files_left = num_files - num_files_reviewed
    print(f"> {remaining} lines remaining | {pct}% reviewed | {files_left} files touched")


def cmd_review(path, mode, key):
    state = load_state(key)
    if not state or path not in state["files"]:
        print("Unknown file. Run 'codereview overview' first.")
        return False
    if state.is_file_reviewed(path):
        print(f"{path} already reviewed")
        return False
    run_review_cmd(path)
    if not yn("Mark reviewed?"):
        return False
    StateManager().mark_file_reviewed(state, path)
    save_state(state)
    lines = state.lines_of_file(path)
    print(f"> Marked {lines} lines as reviewed ({mode} mode)")
    return True


def cmd_reset():
    key = current_key()
    state = load_state(key)
    StateManager().do_reset(state)


def _interactive_session(paths, key):
    approved = []
    def valid_ids(ids):
        for i in (ids or []):
            if not i.isdigit() or not (1 <= int(i) <= len(paths)):
                print(f"invalid file id: {i}")
                continue
            yield i

    def print_files(ids):
        for i in valid_ids(ids):
            path = paths[int(i) - 1]
            full_path = os.path.join(repo_root(), path)
            print(f"== {full_path} ==")

    def review_files(ids, mode):
        approved_here = []
        for i in valid_ids(ids):
            path = paths[int(i) - 1]
            if cmd_review(path, mode, key):
                approved_here.append(path)
        return approved_here

    def list_all():
        state = load_state(key) or {"files": {}}
        for idx, path in enumerate(paths, 1):
            lines = state.lines_of_file(path)
            print(f"{idx}. {path:25} +{lines}")

    def list_unreviewed():
        state = load_state(key) or {"files": {}}
        for idx, path in enumerate(paths, 1):
            if not state.is_file_reviewed(path):
                lines = state.lines_of_file(path)
                print(f"{idx}. {path:25} +{lines}")

    cmds = {
        "p": print_files,
        "print": print_files,
        "rs": lambda ids: review_files(ids, "skim"),
        "rd": lambda ids: review_files(ids, "deep"),
        "ls": list_all,
        "todo": list_unreviewed,
        "td": list_unreviewed,
    }

    print("commands: p <ids>, rs <ids>, rd <ids>, ls, todo/td, empty line to exit")
    while True:
        try:
            entry = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not entry:
            break
        parts = entry.split()
        if all(p.isdigit() for p in parts):
            cmd, ids = "rs", parts
        else:
            cmd, *ids = parts
        fn = cmds.get(cmd)
        if not fn:
            print("unknown command")
        else:
            res = fn(ids)
            if res:
                approved.extend(res)
        cmd_status()
    if approved:
        print("\nApproved in this session:")
        for pth in approved:
            print(f"- {pth}")


def main():
    config = load_config()
    aliases = config.get("aliases", {})
    if len(sys.argv) > 1 and sys.argv[1] in aliases:
        expanded = shlex.split(aliases[sys.argv[1]])
        sys.argv = [sys.argv[0]] + expanded + sys.argv[2:]

    instruction = parse_args_from_cli()
    if instruction:
        match instruction.command:
            case Commands.INIT:
                is_force = CommandOptions.INIT_FORCE in instruction.options
                return cmd_init(review_id=instruction.reviewId, force=is_force)
            case Commands.OVERVIEW:
                is_interactive = CommandOptions.INTERACTIVE in instruction.options
                return cmd_overview(config, is_interactive)
            case Commands.STATUS:
                return cmd_status()
            case Commands.RESET:
                return cmd_reset()
            case Commands.REVIEW:
                mode = "deep" if CommandOptions.REVIEW_DEEP in instruction.options else "skim"
                return cmd_review(instruction.filePath, mode, current_key())
    print_usage()


if __name__ == "__main__":
    main()
