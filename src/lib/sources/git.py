from dataclasses import dataclass, field
import subprocess
from typing import List, Optional

@dataclass
class GitData:
    title: Optional[str] = None
    body: Optional[str] = None
    number: Optional[int] = None
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
