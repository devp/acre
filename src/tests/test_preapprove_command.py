from __future__ import annotations

import json


def test_preapprove_command_adds_block(tmp_path, monkeypatch, capsys):
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

    # Run: `acre preapprove f.py 10 12 --notes skip`
    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    parse_args_from_cli(
        context=ctx,
        override_args=["preapprove", "f.py", "10:12", "--notes", "skip"],
    )

    out = capsys.readouterr().out
    assert "Preapproved" in out

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    blocks = raw["files"]["f.py"]["preapproved_blocks"]
    assert blocks == [{"start_line": 10, "end_line": 12, "notes": "skip"}]


def test_preapprove_colon_prefix_range(tmp_path, capsys):
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

    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    parse_args_from_cli(context=ctx, override_args=["preapprove", "f.py", ":5"])

    import json  # noqa: PLC0415

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    blocks = raw["files"]["f.py"]["preapproved_blocks"]
    assert blocks == [{"start_line": 1, "end_line": 5, "notes": ""}]


def test_preapprove_open_end_range(tmp_path, monkeypatch, capsys):
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
        lambda *_a, **_kw: ["a\n", "b\n", "c\n", "d\n", "e\n"],
    )

    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    parse_args_from_cli(context=ctx, override_args=["preapprove", "f.py", "3:"])

    import json  # noqa: PLC0415

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    blocks = raw["files"]["f.py"]["preapproved_blocks"]
    assert blocks == [{"start_line": 3, "end_line": 5, "notes": ""}]
