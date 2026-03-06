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

