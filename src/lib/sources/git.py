import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GitData:
    title: Optional[str] = None
    body: Optional[str] = None
    number: Optional[int] = None
    url: Optional[str] = None
    files: List[str] = field(default_factory=list)
    lines_changed: dict[str, int] = field(default_factory=dict)
    base_commit: Optional[str] = None
    head_commit: Optional[str] = None


def get_repo_root() -> str:
    """Get repository root directory"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        raise ValueError("Not in a git repository")

def get_current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        raise ValueError("Unable to get current branch")

def get_name_rev() -> str:
    """This works if on detached head."""
    try:
        result = subprocess.run(
            ["git", "name-rev", "--name-only", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().replace("", "")
    except subprocess.CalledProcessError:
        raise ValueError("Unable to get current branch")

def get_current_commit_sha() -> str:
    """Get current commit SHA"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        raise ValueError("Unable to get current commit SHA")

def diff(path, diff_target = "main"):
    args = ["git", "diff", diff_target, "--", path]
    subprocess.run(args)

def diff_filtered(
    path: str,
    *,
    diff_target: str = "main",
    line_patterns: list[str],
) -> int:
    """
    Print a filtered diff for a file, based on regex patterns matched against changed lines.

    - Only considers changed lines (those starting with '+' or '-') excluding file headers.
    - Each pattern is tested against both the raw line (including +/-) and the stripped content.
    Returns the number of matching lines printed.
    """
    result = subprocess.run(
        ["git", "diff", diff_target, "--", path],
        check=False,
        capture_output=True,
        text=True,
    )
    text = result.stdout or ""
    if not text or not line_patterns:
        return 0

    candidates: list[str] = []
    for line in text.splitlines():
        if not line or line[0] not in {"+", "-"}:
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        candidates.append(line)

    if not candidates:
        return 0

    try:
        # test_diff_patterns are documented as grep -E (ERE) patterns; use grep for POSIX class support.
        def _grep_matching_line_numbers(lines: list[str]) -> list[int]:
            grep_args = ["grep", "-n", "-E"]
            for p in line_patterns:
                grep_args.extend(["-e", p])
            grep = subprocess.run(
                grep_args,
                input="\n".join(lines) + "\n",
                text=True,
                capture_output=True,
                check=False,
            )
            if grep.returncode != 0:
                # 1 = no matches; 2 = grep error. In either case, treat as no matches.
                return []
            out = grep.stdout or ""
            nums: list[int] = []
            for ln in out.splitlines():
                if not ln:
                    continue
                prefix, _sep, _rest = ln.partition(":")
                try:
                    nums.append(int(prefix))
                except ValueError:
                    continue
            return nums

        raw_nums = _grep_matching_line_numbers(candidates)
        stripped_nums = _grep_matching_line_numbers([c[1:] for c in candidates])
        matched_nums: list[int] = []
        seen: set[int] = set()
        for n in raw_nums + stripped_nums:
            if n not in seen:
                seen.add(n)
                matched_nums.append(n)
    except FileNotFoundError:
        return 0

    if not matched_nums:
        return 0

    printed = 0
    for n in matched_nums:
        idx = n - 1
        if 0 <= idx < len(candidates):
            print(candidates[idx], file=sys.stdout)
            printed += 1
    return printed

def get_files_in_range(git_range: str) -> list[str]:
    """Get list of files changed in a git range"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", git_range],
            check=True,
            capture_output=True,
            text=True,
        )
        return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Invalid git range '{git_range}': {e}")

def get_lines_changed_in_range(git_range: str) -> dict[str, int]:
    """Get lines changed per file in a git range"""
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", git_range],
            check=True,
            capture_output=True,
            text=True,
        )
        lines_changed = {}
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 3:
                    added = int(parts[0]) if parts[0] != '-' else 0
                    deleted = int(parts[1]) if parts[1] != '-' else 0
                    filepath = parts[2]
                    lines_changed[filepath] = added + deleted
        return lines_changed
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Invalid git range '{git_range}': {e}")

def get_commit_sha_from_range(git_range: str) -> str:
    """Get the target commit SHA from a git range (the 'to' part)"""
    try:
        if '..' in git_range:
            to_ref = git_range.split('..')[-1]
        else:
            to_ref = git_range
        
        result = subprocess.run(
            ["git", "rev-parse", to_ref],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Invalid git reference '{git_range}': {e}")

def data_from_git_range(git_range: str) -> GitData:
    """Get data from a git range instead of GitHub PR"""
    try:
        files = get_files_in_range(git_range)
        lines_changed = get_lines_changed_in_range(git_range)
        head_commit = get_commit_sha_from_range(git_range)
        
        # Extract base commit from range if specified
        base_commit = None
        if '..' in git_range:
            base_ref = git_range.split('..')[0]
            try:
                result = subprocess.run(
                    ["git", "rev-parse", base_ref],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                base_commit = result.stdout.strip()
            except subprocess.CalledProcessError:
                pass
        
        return GitData(
            title=f"Git range: {git_range}",
            body=f"Changes from git range {git_range}",
            number=None,
            files=files,
            lines_changed=lines_changed,
            base_commit=base_commit,
            head_commit=head_commit,
        )
    except ValueError as e:
        raise ValueError(f"Failed to get data from git range '{git_range}': {e}")
