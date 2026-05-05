from __future__ import annotations

import json


def test_preapprove_hunk_records_hunk_line_range(tmp_path, monkeypatch):
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
        "lib.commands.preapprove.diff_lines",
        lambda *_args, **_kwargs: [
            "diff --git a/f.py b/f.py\n",
            "--- a/f.py\n",
            "+++ b/f.py\n",
            "\x1b[36m@@ -1,1 +1,1 @@\x1b[0m\n",
            "-old\n",
            "+new\n",
            "\x1b[36m@@ -10,1 +10,1 @@\x1b[0m\n",
            "-foo\n",
            "+bar\n",
        ],
    )

    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    # Preapprove the first hunk (lines 4-6 in the rendered diff output).
    parse_args_from_cli(context=ctx, override_args=["preapprove", "1", "--hunk", "1"])

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    blocks = raw["files"]["f.py"]["preapproved_blocks"]
    assert blocks == [{"start_line": 4, "end_line": 6, "notes": ""}]
