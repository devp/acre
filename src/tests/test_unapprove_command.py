from __future__ import annotations

import json

import pytest


def _make_ctx(tmp_path, *, files):
    from lib.state import StateManager  # noqa: PLC0415
    from lib.models import ReviewState  # noqa: PLC0415
    from cli.context import Context  # noqa: PLC0415

    (tmp_path / ".git").mkdir()
    mgr = StateManager(repo_root=str(tmp_path), current_sha="headsha")
    state = ReviewState(
        review_id="r1",
        init_commit_sha="initsha",
        files=files,
        metadata={"base_commit": "base", "head_commit": "head"},
    )
    mgr.save_state(state)
    return Context(key="r1", state_manager=mgr, config={})


def test_unapprove_clears_approved_sha_by_path(tmp_path, capsys):
    from lib.models import FileState  # noqa: PLC0415
    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    ctx = _make_ctx(tmp_path, files={"f.py": FileState(lines=1, approved_sha="headsha")})

    parse_args_from_cli(context=ctx, override_args=["unapprove", "f.py"])

    out = capsys.readouterr().out
    assert "Unapproved 1 file(s): f.py" in out

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    assert raw["files"]["f.py"]["approved_sha"] is None


def test_unapprove_resolves_numeric_index(tmp_path, capsys):
    from lib.models import FileState  # noqa: PLC0415
    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    ctx = _make_ctx(
        tmp_path,
        files={
            "a.py": FileState(lines=1, approved_sha="headsha"),
            "b.py": FileState(lines=1, approved_sha="headsha"),
        },
    )

    parse_args_from_cli(context=ctx, override_args=["unapprove", "2"])

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    assert raw["files"]["a.py"]["approved_sha"] == "headsha"
    assert raw["files"]["b.py"]["approved_sha"] is None


def test_unapprove_accepts_multiple_items(tmp_path):
    from lib.models import FileState  # noqa: PLC0415
    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    ctx = _make_ctx(
        tmp_path,
        files={
            "a.py": FileState(lines=1, approved_sha="headsha"),
            "b.py": FileState(lines=1, approved_sha="headsha"),
        },
    )

    parse_args_from_cli(context=ctx, override_args=["unapprove", "a.py", "b.py"])

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    assert raw["files"]["a.py"]["approved_sha"] is None
    assert raw["files"]["b.py"]["approved_sha"] is None


def test_unapprove_leaves_preapproved_blocks_untouched(tmp_path):
    from lib.models import FileState, PreApprovalBlock  # noqa: PLC0415
    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    ctx = _make_ctx(
        tmp_path,
        files={
            "f.py": FileState(
                lines=1,
                approved_sha="headsha",
                preapproved_blocks=[PreApprovalBlock(start_line=1, end_line=2, notes="n")],
            )
        },
    )

    parse_args_from_cli(context=ctx, override_args=["unapprove", "f.py"])

    raw = json.loads((tmp_path / ".git" / "acre" / "r1.json").read_text())
    assert raw["files"]["f.py"]["approved_sha"] is None
    assert raw["files"]["f.py"]["preapproved_blocks"] == [
        {"start_line": 1, "end_line": 2, "notes": "n"}
    ]


def test_unapprove_requires_at_least_one_item(tmp_path):
    from lib.models import FileState  # noqa: PLC0415
    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    ctx = _make_ctx(tmp_path, files={"f.py": FileState(lines=1, approved_sha="headsha")})

    with pytest.raises(SystemExit):
        parse_args_from_cli(context=ctx, override_args=["unapprove"])


def test_unapprove_unknown_file_reports_error_and_exits(tmp_path, capsys):
    from lib.models import FileState  # noqa: PLC0415
    from cli.parser import parse_args_from_cli  # noqa: PLC0415

    ctx = _make_ctx(tmp_path, files={"f.py": FileState(lines=1, approved_sha="headsha")})

    with pytest.raises(SystemExit):
        parse_args_from_cli(context=ctx, override_args=["unapprove", "nope.py"])

    out = capsys.readouterr().out
    assert "No matching files found" in out


def test_unapprove_not_registered_in_interactive_parser(capsys):
    from lib.commands.interactive import _build_interactive_parser  # noqa: PLC0415

    p = _build_interactive_parser(config={})
    with pytest.raises(SystemExit):
        p.parse_args(["unapprove", "f.py"])
    assert "invalid choice: 'unapprove'" in capsys.readouterr().err
