from __future__ import annotations


def test_review_diff_line_numbers_prefixes_output_lines(tmp_path, monkeypatch, capsys):
    (tmp_path / ".git").mkdir()

    from lib.models import FileState, ReviewState  # noqa: PLC0415
    from lib.state import StateManager  # noqa: PLC0415
    from cli.context import Context  # noqa: PLC0415

    mgr = StateManager(repo_root=str(tmp_path), current_sha="headsha")
    state = ReviewState(
        review_id="r1",
        init_commit_sha="initsha",
        files={"f.py": FileState(lines=1)},
        metadata={"base_commit": "base", "head_commit": "head"},
    )
    mgr.save_state(state)
    ctx = Context(key="r1", state_manager=mgr, config={})

    monkeypatch.setattr(
        "lib.commands_v0.diff_lines",
        lambda *_args, **_kwargs: ["a\n", "b\n"],
    )

    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    parse_args_from_cli(
        context=ctx,
        override_args=["review", "1", "--skim", "--diff-line-numbers"],
    )

    out = capsys.readouterr().out
    assert "  1:" in out
    assert "  2:" in out

