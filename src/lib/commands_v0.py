import shlex
import subprocess
from cli.util import yn
from lib.sources.github import data_from_gh
from lib.sources.jira import find_jira_tag
from lib.state import StateManager


def run_review_cmd(path, config):
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


class CommandsV0:
    """Simple earlier versions of some commands."""

    def __init__(self, state_manager: StateManager, key: str, config={}):
        self.key = key
        self.config = config
        self.state_manager = state_manager
        _state = self.state_manager.load_state(key)
        if not _state:
            raise Exception("No state file: run init first")
        self.state = _state

    def cmd_overview(self):
        data = data_from_gh()
        title = data.title or ""
        body = data.body or ""
        files = data.files
        print(f"\U0001F4CC PR Summary: {title}")
        jira = find_jira_tag(data)
        jira_base = self.config.get("jira", {}).get("base")
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


    def cmd_review(self, path, mode="default"):
        if self.state.is_file_reviewed(path):
            print(f"{path} already reviewed")
            return False
        run_review_cmd(path, self.config)
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



