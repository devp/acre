import subprocess

import pytest

import lib.sources.git as git


class _Res:
    def __init__(self, stdout: str):
        self.stdout = stdout


def test_get_lines_changed_in_range_parses_numstat(monkeypatch):
    def run(cmd, **_kwargs):
        assert cmd[:3] == ["git", "diff", "--numstat"]
        return _Res("3\t2\ta.py\n-\t5\tbin.dat\n0\t1\tb.py\n")

    monkeypatch.setattr(git.subprocess, "run", run)
    assert git.get_lines_changed_in_range("main..HEAD") == {"a.py": 5, "bin.dat": 5, "b.py": 1}


def test_get_files_in_range_parses_name_only(monkeypatch):
    def run(cmd, **_kwargs):
        assert cmd[:4] == ["git", "diff", "--name-only", "main..HEAD"]
        return _Res("a.py\n\nb.py\n")

    monkeypatch.setattr(git.subprocess, "run", run)
    assert git.get_files_in_range("main..HEAD") == ["a.py", "b.py"]


def test_get_commit_sha_from_range_uses_to_ref(monkeypatch):
    def run(cmd, **_kwargs):
        assert cmd == ["git", "rev-parse", "HEAD"]
        return _Res("abc123\n")

    monkeypatch.setattr(git.subprocess, "run", run)
    assert git.get_commit_sha_from_range("main..HEAD") == "abc123"


def test_get_lines_changed_in_range_wraps_called_process_error(monkeypatch):
    def run(_cmd, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["git", "diff"])

    monkeypatch.setattr(git.subprocess, "run", run)
    with pytest.raises(ValueError, match="Invalid git range 'main..HEAD'"):
        git.get_lines_changed_in_range("main..HEAD")


def test_data_from_git_range_wraps_failures(monkeypatch):
    monkeypatch.setattr(git, "get_files_in_range", lambda _r: (_ for _ in ()).throw(ValueError("bad")))
    with pytest.raises(ValueError, match="Failed to get data from git range 'main..HEAD'"):
        git.data_from_git_range("main..HEAD")


def test_get_default_branch_uses_symbolic_ref(monkeypatch):
    def run(cmd, **_kwargs):
        assert cmd == ["git", "symbolic-ref", "refs/remotes/origin/HEAD"]
        return _Res("refs/remotes/origin/main\n")

    monkeypatch.setattr(git.subprocess, "run", run)
    assert git.get_default_branch() == "main"


def test_get_default_branch_falls_back_to_remote_show(monkeypatch):
    calls = []

    def run(cmd, **_kwargs):
        calls.append(cmd)
        if cmd[1] == "symbolic-ref":
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
        assert cmd == ["git", "remote", "show", "origin"]
        return _Res("* remote origin\n  HEAD branch: develop\n  Remote branches:\n")

    monkeypatch.setattr(git.subprocess, "run", run)
    assert git.get_default_branch() == "develop"
    assert len(calls) == 2


def test_get_default_branch_raises_when_undetectable(monkeypatch):
    def run(cmd, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(git.subprocess, "run", run)
    with pytest.raises(ValueError, match="Unable to determine default branch"):
        git.get_default_branch()


def test_resolve_upbranch_range_uses_merge_base_with_default_branch(monkeypatch):
    monkeypatch.setattr(git, "get_default_branch", lambda: "main")

    def run(cmd, **_kwargs):
        assert cmd == ["git", "merge-base", "main", "HEAD"]
        return _Res("deadbeef\n")

    monkeypatch.setattr(git.subprocess, "run", run)
    assert git.resolve_upbranch_range() == "deadbeef..HEAD"


def test_resolve_upbranch_range_wraps_merge_base_failure(monkeypatch):
    monkeypatch.setattr(git, "get_default_branch", lambda: "main")

    def run(_cmd, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["git", "merge-base"])

    monkeypatch.setattr(git.subprocess, "run", run)
    with pytest.raises(ValueError, match="Unable to find merge base with 'main'"):
        git.resolve_upbranch_range()

