import os
import re
import subprocess
from hashlib import sha256

from cli.pretty import print_whimsically
from cli.util import mark_reviewed_prompt, open_url, yn
from lib.config.config import get_review_test_diff_patterns, get_review_test_file_patterns
from lib.commands.preapprove import _find_hunk_range, _parse_range_arg
from lib.diff_filter import excluded_diff_line_numbers, filter_diff_lines
from lib.hunk_filter import _strip_ansi, filter_diff_hunks_by_regex
from lib.sources.git import diff_filtered, diff_lines
from lib.sources.github import approve_pr, data_from_gh
from lib.sources.jira import find_jira_tag
from lib.state import StateManagerProtocol



class CommandsV0:
    """Simple earlier versions of some commands."""

    def __init__(self, state_manager: StateManagerProtocol, key: str, config={}):
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
        test_patterns = get_review_test_file_patterns(self.config)
        compiled_test_patterns = [re.compile(p) for p in test_patterns] if test_patterns else []
        for idx, path in enumerate(self.state.files, 1):
            reviewed = self.state.is_file_reviewed(path)
            if todo_only and reviewed:
                continue
            if raw:
                print(path)
                continue
            file = self.state.files.get(path)
            lines = file.lines if file else 0
            pa_count = len(file.preapproved_blocks) if file and file.preapproved_blocks else 0
            pa_str = f" [{pa_count} PA]" if pa_count else ""
            mark = "\u2705 " if reviewed else ""
            padded_path = f"{path:25}"
            basename = os.path.basename(path)
            is_test = any(p.search(basename) for p in compiled_test_patterns)
            colored_path = f"\033[96m{padded_path}\033[0m" if is_test else padded_path
            print(f"{idx}. {mark}{colored_path} Δ{lines}{pa_str}")

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

    def resolve_review_path(self, item: str) -> str | None:
        if item in self.state.files:
            return item

        if item.isdigit():
            idx = int(item) - 1
            paths = list(self.state.files.keys())
            if 0 <= idx < len(paths):
                return paths[idx]
            return None

        matches = [path for path in self.state.files if os.path.basename(path) == item]
        if len(matches) == 1:
            return matches[0]
        return None

    def github_file_url(self, path: str) -> str | None:
        pr_url = self.state.metadata.get("pr_url")
        if not pr_url:
            data = data_from_gh()
            pr_url = data.url
            if pr_url:
                self.state.metadata["pr_url"] = pr_url
                self.state_manager.save_state(self.state)
        if not pr_url:
            return None
        return f"{pr_url}/files#diff-{sha256(path.encode('utf-8')).hexdigest()}"

    def cmd_peek(self, item: str) -> bool:
        path = self.resolve_review_path(item)
        if not path:
            print(f"Could not resolve file: {item}")
            return False

        url = self.github_file_url(path)
        if not url:
            print("No GitHub PR URL found in review metadata. Run 'init' on a branch with a GitHub PR.")
            return False

        if not open_url(url):
            print(f"Failed to open URL for {path}")
            return False

        print(f"Opened {path} in GitHub PR diff view.")
        return True

    def cmd_review(
        self,
        path,
        mode="default",
        ask_approve=True,
        test_diff_first: bool = False,
        focus_regex: str | None = None,
        regex_include_context: bool = False,
        show_diff_line_numbers: bool = False,
        show_hunk_numbers: bool = False,
    ):
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

        def _render_diff() -> None:
            file_state = self.state.files.get(path)
            lines = diff_lines(path, diff_target=self.state.diff_target())

            if focus_regex:
                lines = filter_diff_hunks_by_regex(
                    lines, pattern=focus_regex, include_context=regex_include_context
                )

            preapproved_blocks = file_state.preapproved_blocks if file_state else []
            excluded = (
                excluded_diff_line_numbers(preapproved_blocks=preapproved_blocks)
                if preapproved_blocks
                else set()
            )

            if show_diff_line_numbers:
                # Numbers always refer to pre-preapproval positions so they stay stable
                # across multiple preapprove calls.
                rendered: list[str] = []
                hunk_idx = 0
                for idx, line in enumerate(lines, start=1):
                    if idx in excluded:
                        continue
                    if show_hunk_numbers and _strip_ansi(line).startswith("@@"):
                        hunk_idx += 1
                        prefix = f"\033[2m{idx:3d}: H{hunk_idx:02d} \033[0m"
                    else:
                        prefix = f"\033[2m{idx:3d}: \033[0m"
                    rendered.append(f"{prefix}{line}")
                lines = rendered
            else:
                if excluded:
                    lines = filter_diff_lines(lines, preapproved_blocks=preapproved_blocks)
                if show_hunk_numbers:
                    annotated: list[str] = []
                    hunk_idx = 0
                    for line in lines:
                        if _strip_ansi(line).startswith("@@"):
                            hunk_idx += 1
                            annotated.append(f"H{hunk_idx:02d} {line}")
                        else:
                            annotated.append(line)
                    lines = annotated

            print("".join(lines), end="")

        _render_diff()

        if not ask_approve:
            return

        def _on_preapprove(range_str: str) -> None:
            mode_p, hunk_num, start_line_p, end_line_p = _parse_range_arg(range_str)
            if mode_p == "invalid":
                print(f"Invalid range: {range_str!r}")
                return
            current_state = self.state_manager.load_state(self.key)
            if current_state is None:
                return
            if mode_p == "hunk":
                assert hunk_num is not None
                all_lines = diff_lines(path, diff_target=current_state.diff_target())
                s, e = _find_hunk_range(all_lines, hunk_num)
                if s is None or e is None:
                    print(f"Hunk {hunk_num} not found")
                    return
                self.state_manager.add_preapproved_block(current_state, path=path, start_line=s, end_line=e)
                self.state_manager.save_state(current_state)
                print(f"Preapproved hunk {hunk_num} (lines {s}-{e}) of {path}")
            else:
                s = start_line_p if start_line_p is not None else 1
                if end_line_p is None:
                    all_lines = diff_lines(path, diff_target=current_state.diff_target())
                    e = len(all_lines)
                else:
                    e = end_line_p
                self.state_manager.add_preapproved_block(current_state, path=path, start_line=s, end_line=e)
                self.state_manager.save_state(current_state)
                print(f"Preapproved lines {s}-{e} of {path}")
            self.state = current_state
            _render_diff()

        if not mark_reviewed_prompt(
            path=path,
            prompt="Mark reviewed?",
            on_peek=lambda: self.cmd_peek(path),
            on_preapprove=_on_preapprove,
        ):
            return
        self.state_manager.mark_file_reviewed(self.state, path)
        self.state_manager.save_state(self.state)
        reviewed_lines = self.state.lines_of_file(path)
        print(f"> Marked {reviewed_lines} lines as reviewed ({mode} mode)")

    def cmd_reset(self):
        self.state_manager.do_reset(self.state)
        self.state_manager.save_state(self.state)

    def cmd_approve(self):
        pr_number = self.state.metadata.get("pr_number")
        if not pr_number:
            print("No PR number found in review metadata. Run 'init' on a branch with a GitHub PR.")
            return False
        if not yn(f"Approve PR #{pr_number}?", default=False):
            print("Approval cancelled.")
            return False
        try:
            approve_pr(pr_number)
        except FileNotFoundError:
            print("GitHub CLI 'gh' is not installed or not on PATH.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Failed to approve PR #{pr_number} (exit code {e.returncode}).")
            return False
        print(f"Approved PR #{pr_number}.")
        return True
