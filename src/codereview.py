#!/usr/bin/env python3
import argparse
import json
import os
import re
import shlex
import subprocess
import sys


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


def current_pr_key():
    try:
        pr = subprocess.run(
            ["gh", "pr", "view", "--json", "number"],
            check=True,
            capture_output=True,
            text=True,
        )
        repo = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        print("unable to determine current PR")
        sys.exit(1)
    number = json.loads(pr.stdout).get("number")
    return str(number)


def state_file(pr_key):
    base = os.path.join(repo_root(), ".git", "codereview_state")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{pr_key}.json")


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


def load_state(pr_key):
    path = state_file(pr_key)
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    if yn("No state file. Run overview?"):
        cmd_overview(load_config())
        return load_state(pr_key)
    return None


def save_state(state, pr_key):
    print(pr_key)
    print(state_file(pr_key))
    with open(state_file(pr_key), "w") as fh:
        json.dump(state, fh)


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
    except subprocess.CalledProcessError:
        print("gh pr view failed; ensure you're on a PR branch")
        sys.exit(1)
    return json.loads(res.stdout)


def find_jira(text):
    m = re.search(r"[A-Z][A-Z0-9]+-\d+", text or "")
    return m.group(0) if m else None


def cmd_overview(config, interactive=False):
    pr_key = current_pr_key()
    data = gh_view()
    title = data.get("title", "").strip()
    body = data.get("body").strip() or ""
    print(f"\U0001F4CC PR Summary: {title}")
    jira = find_jira("\n".join([title, body]))
    jira_base = config.get("jira", {}).get("base")
    if jira and jira_base:
        print(f"\U0001F517 Jira: https://{jira_base}.atlassian.net/browse/{jira}")
    elif jira:
        print(f"\U0001F517 Jira: {jira}")
    if body:
        print(f"> {body}")
    files = data.get("files") or []
    state = {"files": {}, "total_lines": 0}
    print("\n\U0001F4C1 File Summary:")
    paths = []
    for idx, f in enumerate(files, 1):
        path = f.get("path")
        lines = f.get("additions", 0) + f.get("deletions", 0)
        state["files"][path] = {"lines": lines, "reviewed": False}
        state["total_lines"] += lines
        paths.append(path)
        mark = "\u2705 " if reviewed else ""
        if interactive:
            print(f"{idx}. {mark}{path:25} +{lines}")
        else:
            print(f"- {mark}{path:25} +{lines}")
    save_state(state, pr_key)
    print(f"\n\U0001F9AE Total: {len(files)} files, {state['total_lines']} changed lines")

    if interactive:
        _interactive_session(paths, pr_key)


def cmd_status(pr_key):
    state = load_state(pr_key)
    if not state:
        print("No state. Run 'codereview overview' first.")
        return
    total = state["total_lines"]
    reviewed = sum(f["lines"] for f in state["files"].values() if f["reviewed"])
    remaining = total - reviewed
    pct = int((reviewed / total) * 100) if total else 100
    files_left = sum(1 for f in state["files"].values() if not f["reviewed"])
    print(f"> {remaining} lines remaining | {pct}% reviewed | {files_left} files touched")


def cmd_review(path, mode, pr_key):
    state = load_state(pr_key)
    if not state or path not in state["files"]:
        print("Unknown file. Run 'codereview overview' first.")
        return False
    if state["files"][path]["reviewed"]:
        print(f"{path} already reviewed")
        return False
    run_review_cmd(path)
    if not yn("Mark reviewed?"):
        return False
    state["files"][path]["reviewed"] = True
    save_state(state, pr_key)
    lines = state["files"][path]["lines"]
    print(f"> Marked {lines} lines as reviewed ({mode} mode)")
    return True


def cmd_reset(pr_key):
    path = state_file(pr_key)
    if os.path.exists(path):
        os.remove(path)
        print("Reset review progress")
    else:
        print("No state to reset")


def _interactive_session(paths, pr_key):
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
            if cmd_review(path, mode, pr_key):
                approved_here.append(path)
        return approved_here

    def list_all(_ids=None):
        state = load_state(pr_key) or {"files": {}}
        for idx, path in enumerate(paths, 1):
            lines = state["files"].get(path, {}).get("lines", 0)
            print(f"{idx}. {path:25} +{lines}")

    def list_unreviewed(_ids=None):
        state = load_state(pr_key) or {"files": {}}
        for idx, path in enumerate(paths, 1):
            if not state["files"].get(path, {}).get("reviewed"):
                lines = state["files"].get(path, {}).get("lines", 0)
                print(f"{idx}. {path:25} +{lines}")

    cmds = {
        "p": print_files,
        "print": print_files,
        "rs": lambda ids: review_files(ids, "skim"),
        "rd": lambda ids: review_files(ids, "deep"),
        "ls": lambda ids: list_all(),
        "lsu": lambda ids: list_unreviewed(),
    }

    print("commands: p <ids>, rs <ids>, rd <ids>, ls, lsu, empty line to exit")
    while True:
        try:
            entry = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not entry:
            break
        cmd, *ids = entry.split()
        fn = cmds.get(cmd)
        if not fn:
            print("unknown command")
        else:
            res = fn(ids)
            if res:
                approved.extend(res)
        cmd_status(pr_key)
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

    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    over = sub.add_parser("overview")
    over.add_argument("-i", "--interactive", action="store_true")
    sub.add_parser("status")
    sub.add_parser("reset")
    r = sub.add_parser("review")
    r.add_argument("file")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--skim", action="store_true")
    g.add_argument("--deep", action="store_true")
    args = p.parse_args()
    if args.cmd == "overview":
        cmd_overview(config, args.interactive)
    elif args.cmd == "status":
        cmd_status(current_pr_key())
    elif args.cmd == "reset":
        cmd_reset(current_pr_key())
    elif args.cmd == "review":
        mode = "deep" if args.deep else "skim"
        cmd_review(args.file, mode, current_pr_key())
    else:
        p.print_help()


if __name__ == "__main__":
    main()
