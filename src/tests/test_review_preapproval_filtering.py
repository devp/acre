from __future__ import annotations


def test_review_hides_preapproved_lines_from_diff(tmp_path, monkeypatch, capsys):
    """Preapproved line ranges should be absent from the rendered diff output."""
    (tmp_path / ".git").mkdir()

    from lib.models import FileState, ReviewState, PreApprovalBlock  # noqa: PLC0415
    from lib.state import StateManager  # noqa: PLC0415
    from cli.context import Context  # noqa: PLC0415

    mgr = StateManager(repo_root=str(tmp_path), current_sha="headsha")
    fs = FileState(lines=2)
    fs.preapproved_blocks = [PreApprovalBlock(start_line=2, end_line=2)]
    state = ReviewState(
        review_id="r1",
        init_commit_sha="initsha",
        files={"f.py": fs},
        metadata={"base_commit": "base", "head_commit": "head"},
    )
    mgr.save_state(state)
    ctx = Context(key="r1", state_manager=mgr, config={})

    monkeypatch.setattr(
        "lib.commands_v0.diff_lines",
        lambda *_a, **_kw: ["-old\n", "+new\n", "+keep\n"],
    )
    monkeypatch.setattr("lib.commands.review.yn", lambda *_, **__: False)

    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    parse_args_from_cli(context=ctx, override_args=["review", "1", "--skim"])

    out = capsys.readouterr().out
    assert "+new" not in out
    assert "+keep" in out
