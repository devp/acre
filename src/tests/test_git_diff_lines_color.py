from __future__ import annotations


def test_diff_lines_forces_color_when_delta_missing(monkeypatch):
    captured = {}

    def fake_which(name):
        return None

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class R:
            stdout = ""

        return R()

    import shutil  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)

    from lib.sources.git import diff_lines  # noqa: PLC0415

    diff_lines("f.py", diff_target="a..b")

    assert "--color=always" in captured["args"]


def test_diff_lines_pipes_through_delta_when_available(monkeypatch):
    calls = []

    def fake_which(name):
        return "/usr/bin/delta" if name == "delta" else None

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))

        class R:
            stdout = "\x1b[32m+highlighted\x1b[0m\n" if args[0] == "/usr/bin/delta" else "+plain\n"

        return R()

    import shutil  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)

    from lib.sources.git import diff_lines  # noqa: PLC0415

    lines = diff_lines("f.py", diff_target="a..b")

    assert len(calls) == 2
    git_args, git_kwargs = calls[0]
    delta_args, delta_kwargs = calls[1]

    assert git_args[:2] == ["git", "diff"]
    assert "--color=always" not in git_args

    assert delta_args[0] == "/usr/bin/delta"
    assert "--color-only" in delta_args
    assert delta_kwargs["input"] == "+plain\n"

    assert lines == ["\x1b[32m+highlighted\x1b[0m\n"]
