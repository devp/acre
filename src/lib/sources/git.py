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

def diff(path, diff_target = "main"):
    args = ["git", "diff", diff_target, "--", path]
    subprocess.run(args)

def resolve_ref(ref: str) -> str:
    """Resolve a git reference to its SHA"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", ref],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        raise ValueError(f"Unable to resolve reference: {ref}")

def get_commit_parent(commit_sha: str) -> str:
    """Get the parent commit SHA"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", f"{commit_sha}~1"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        raise ValueError(f"Unable to get parent of commit: {commit_sha}")
