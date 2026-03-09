import subprocess

from lib.commands_v0 import CommandsV0
from lib.models import ReviewState
from lib.state import StateManager


def test_cmd_approve_confirms_and_runs_gh(monkeypatch, tmp_path, capsys):
    state_manager = StateManager(repo_root=str(tmp_path), current_sha="deadbeef")
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        metadata={"pr_number": "123"},
    )
    state_manager.save_state(state)

    calls: list[str] = []

    monkeypatch.setattr("lib.commands_v0.yn", lambda _prompt, default=False: True)
    monkeypatch.setattr("lib.sources.github.subprocess.run", lambda cmd, **_kwargs: calls.append(" ".join(cmd)))

    cmd = CommandsV0(state_manager=state_manager, key="rid", config={})

    assert cmd.cmd_approve() is True
    assert calls == ["gh pr review --approve 123"]
    assert "Approved PR #123." in capsys.readouterr().out


def test_cmd_approve_cancelled_does_not_run_gh(monkeypatch, tmp_path, capsys):
    state_manager = StateManager(repo_root=str(tmp_path), current_sha="deadbeef")
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        metadata={"pr_number": "123"},
    )
    state_manager.save_state(state)

    monkeypatch.setattr("lib.commands_v0.yn", lambda _prompt, default=False: False)

    def _fail(*_args, **_kwargs):
        raise AssertionError("gh should not be called when approval is cancelled")

    monkeypatch.setattr("lib.sources.github.subprocess.run", _fail)

    cmd = CommandsV0(state_manager=state_manager, key="rid", config={})

    assert cmd.cmd_approve() is False
    assert "Approval cancelled." in capsys.readouterr().out


def test_cmd_approve_requires_pr_number(tmp_path, capsys):
    state_manager = StateManager(repo_root=str(tmp_path), current_sha="deadbeef")
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        metadata={},
    )
    state_manager.save_state(state)

    cmd = CommandsV0(state_manager=state_manager, key="rid", config={})

    assert cmd.cmd_approve() is False
    assert "No PR number found in review metadata." in capsys.readouterr().out


def test_cmd_approve_reports_gh_failure(monkeypatch, tmp_path, capsys):
    state_manager = StateManager(repo_root=str(tmp_path), current_sha="deadbeef")
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        metadata={"pr_number": "123"},
    )
    state_manager.save_state(state)

    monkeypatch.setattr("lib.commands_v0.yn", lambda _prompt, default=False: True)

    def _raise(*_args, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["gh"])

    monkeypatch.setattr("lib.sources.github.subprocess.run", _raise)

    cmd = CommandsV0(state_manager=state_manager, key="rid", config={})

    assert cmd.cmd_approve() is False
    assert "Failed to approve PR #123" in capsys.readouterr().out
