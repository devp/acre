from __future__ import annotations


def test_diff_lines_forces_color(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class R:
            stdout = ""

        return R()

    import subprocess  # noqa: PLC0415

    monkeypatch.setattr(subprocess, "run", fake_run)

    from lib.sources.git import diff_lines  # noqa: PLC0415

    diff_lines("f.py", diff_target="a..b")

    assert "--color=always" in captured["args"]

