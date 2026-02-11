import os
import re

from cli.pretty import print_whimsically
from cli.util import mark_reviewed_prompt, yn
from lib.config.config import get_review_test_diff_patterns, get_review_test_file_patterns
from lib.sources.git import diff, diff_filtered
from lib.sources.github import data_from_gh
from lib.sources.jira import find_jira_tag
from lib.state import StateManager



class CommandsV0:
    """Simple earlier versions of some commands."""

    def __init__(self, state_manager: StateManager, key: str, config={}):
        self.key = key
        self.config = config
        self.state_manager = state_manager
        _state = self.state_manager.load_state(key)
        if not _state:
            print("No state file: run init first")
            exit(1)
        self.state = _state

    def cmd_overview(self):
        data = data_from_gh()
        title = data.title or ""
        body = data.body or ""
        print(f"\U0001F4CC PR Summary: {title}")
        jira = find_jira_tag(data)
        jira_base = self.config.get("jira", {}).get("base")
        if data.number:
            print(f"Ticket: #{data.number}")
        if jira and jira_base:
            print(f"\U0001F517 Jira: https://{jira_base}.atlassian.net/browse/{jira}")
        elif jira:
            print(f"\U0001F517 Jira: {jira}")
        if body:
            print(f"> {body}")
        self.cmd_list_files()
        self.cmd_status()

    def cmd_list_files(self, todo_only=False, raw=False):
        if not raw:
            print("\n\U0001F4C1 File Summary:")
        for idx, path in enumerate(self.state.files, 1):
            reviewed = self.state.is_file_reviewed(path)
            if todo_only and reviewed:
                continue
            if raw:
                print(path)
                continue
            file = self.state.files.get(path)
            lines = file.lines if file else 0
            mark = "\u2705 " if reviewed else ""
            print(f"{idx}. {mark}{path:25} Δ{lines}")

    def cmd_status(self):
        total = self.state.total_lines()
        reviewed = self.state.total_reviewed_lines()
        remaining = total - reviewed
        pct = int((reviewed / total) * 100) if total else (100 if reviewed else 0)
        num_files = len(self.state.files)
        num_files_reviewed = len(self.state.reviewed_files())
        files_left = num_files - num_files_reviewed
        text = f"> {remaining} lines remaining | {pct}% reviewed | {files_left} files touched"
        if files_left == 0 and num_files > 0:
            print_whimsically(text)
        else:
            print(text)

    def cmd_review(self, path, mode="default", ask_approve=True, test_diff_first: bool = False):
        """Reviews a single file"""
        if self.state.is_file_reviewed(path):
            print(f"{path} already reviewed")
            return False
        if test_diff_first:
            file_patterns = get_review_test_file_patterns(self.config)
            diff_patterns = get_review_test_diff_patterns(self.config)
            if file_patterns and diff_patterns:
                basename = os.path.basename(path)
                try:
                    compiled = [re.compile(p) for p in file_patterns]
                except re.error:
                    compiled = []
                if compiled and any(r.search(basename) for r in compiled):
                    print("\nTest diff subset (matched by review.test_diff_patterns):")
                    printed = diff_filtered(
                        path,
                        diff_target=self.state.diff_target(),
                        line_patterns=diff_patterns,
                    )
                    if printed == 0:
                        print("(no matches)")
                    print("")
                    if ask_approve:
                        ans = input("approve [y/R] ").strip().lower()
                        if ans in {"y", "yes"}:
                            self.state_manager.mark_file_reviewed(self.state, path)
                            self.state_manager.save_state(self.state)
                            lines = self.state.lines_of_file(path)
                            print(f"> Marked {lines} lines as reviewed (test preview)")
                            return True
        diff(path, diff_target=self.state.diff_target())
        if not ask_approve:
            return
        if not mark_reviewed_prompt(path=path, prompt="Mark reviewed?"):
            return
        self.state_manager.mark_file_reviewed(self.state, path)
        self.state_manager.save_state(self.state)
        lines = self.state.lines_of_file(path)
        print(f"> Marked {lines} lines as reviewed ({mode} mode)")

    def cmd_reset(self):
        self.state_manager.do_reset(self.state)
        self.state_manager.save_state(self.state)
