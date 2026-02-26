from __future__ import annotations

import json


def test_preapprove_accepts_file_index(tmp_path, capsys):
    (tmp_path / ".git").mkdir()

    from lib.models import FileState, ReviewState  # noqa: PLC0415
    from lib.state import StateManager  # noqa: PLC0415
    from cli.context import Context  # noqa: PLC0415

    mgr = StateManager(repo_root=str(tmp_path), current_sha="headsha")
    state = ReviewState(
        review_id="r1",
        init_commit_sha="initsha",
        files={"a.py": FileState(lines=1), "b.py": FileState(lines=1)},
    )
    mgr.save_state(state)
    ctx = Context(key="r1", state_manager=mgr, config={})

    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    parse_args_from_cli(context=ctx, override_args=["preapprove", "2", "10", "12"])

    out = capsys.readouterr().out
    assert "b.py" in out

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    blocks = raw["files"]["b.py"]["preapproved_blocks"]
    assert blocks == [{"start_line": 10, "end_line": 12, "notes": ""}]

