import subprocess

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
