from __future__ import annotations

import json


def test_review_focus_regex_filters_output_to_matching_hunks(tmp_path, monkeypatch, capsys):
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

    def fake_diff_lines(path: str, diff_target: str = "main") -> list[str]:
        assert path == "f.py"
        assert diff_target == "base..head"
        return [
            "diff --git a/f.py b/f.py\n",
            "--- a/f.py\n",
            "+++ b/f.py\n",
            "@@ -1,1 +1,1 @@\n",
            "-old\n",
            "+new match\n",
            "@@ -10,1 +10,1 @@\n",
            "-foo\n",
            "+bar\n",
        ]

    monkeypatch.setattr("lib.commands_v0.diff_lines", fake_diff_lines)

    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    parse_args_from_cli(context=ctx, override_args=["review", "f.py", "--focus-regex", "match", "--skim"])

    out = capsys.readouterr().out
    assert "+new match" in out
    assert "+bar" not in out

