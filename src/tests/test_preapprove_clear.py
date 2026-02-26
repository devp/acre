from __future__ import annotations

import json


def test_preapprove_clear_removes_blocks(tmp_path):
    (tmp_path / ".git").mkdir()

    from lib.models import FileState, ReviewState, PreApprovalBlock  # noqa: PLC0415
    from lib.state import StateManager  # noqa: PLC0415
    from cli.context import Context  # noqa: PLC0415

    mgr = StateManager(repo_root=str(tmp_path), current_sha="headsha")
    fs = FileState(lines=1)
    fs.preapproved_blocks = [PreApprovalBlock(start_line=1, end_line=2, notes="x")]
    state = ReviewState(review_id="r1", init_commit_sha="initsha", files={"f.py": fs})
    mgr.save_state(state)
    ctx = Context(key="r1", state_manager=mgr, config={})

    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    parse_args_from_cli(context=ctx, override_args=["preapprove", "1", "--clear"])

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    assert raw["files"]["f.py"]["preapproved_blocks"] == []

