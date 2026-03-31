from types import SimpleNamespace

import lib.commands.review as review_cmd
import lib.commands_v0 as commands_v0
import lib.sources.git as git_source
from cli.util import mark_reviewed_prompt as prompt_impl
from lib.models import FileState, ReviewState


def test_cmd_review_test_diff_first_shows_filtered_diff_before_full_diff(monkeypatch):
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"test_widget.py": FileState(lines=1)},
    )

    class FakeStateManager:
        def load_state(self, _key):
            return state

    calls: list[tuple[str, object]] = []

    def fake_diff_filtered(path, *, diff_target, line_patterns):
        calls.append(("diff_filtered", (path, diff_target, tuple(line_patterns))))
        return 1

    def fake_diff(path, diff_target="main"):
        calls.append(("diff", (path, diff_target)))

    monkeypatch.setattr(commands_v0, "diff_filtered", fake_diff_filtered)
    monkeypatch.setattr(commands_v0, "diff", fake_diff)

    cmd = commands_v0.CommandsV0(
        key="rid",
        state_manager=FakeStateManager(),
        config={
            "review": {
                "test_file_patterns": ["^test_"],
                "test_diff_patterns": [
                    "def[[:space:]]+test_",
                    "assert[A-Za-z_]*\\b",
                ],
            }
        },
    )

    cmd.cmd_review("test_widget.py", ask_approve=False, test_diff_first=True)

    assert [c[0] for c in calls] == ["diff_filtered", "diff"]
    assert calls[0][1] == (
        "test_widget.py",
        "main",
        ("def[[:space:]]+test_", "assert[A-Za-z_]*\\b"),
    )


def test_review_impl_passes_test_diff_first_to_cmd_review(monkeypatch):
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"a.py": FileState()},
    )
    calls: list[tuple[str, object]] = []

    class FakeStateManager:
        def load_state(self, _key):
            return state

    class FakeCommandsV0:
        def __init__(self, **_kwargs):
            pass

        def cmd_review(self, *, path, ask_approve=True, test_diff_first=False, **_kwargs):
            calls.append(("review", (path, ask_approve, test_diff_first)))

    monkeypatch.setattr(review_cmd, "CommandsV0", FakeCommandsV0)

    context = SimpleNamespace(key="rid", state_manager=FakeStateManager(), config={})
    args = SimpleNamespace(items=["a.py"], todo=False, skim=False, loc_lte=None, test_diff_first=True)

    review_cmd.impl(args=args, context=context)

    assert calls == [("review", ("a.py", True, True))]


def test_review_impl_uses_config_default_for_test_diff_first(monkeypatch):
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"a.py": FileState()},
    )
    calls: list[tuple[str, object]] = []

    class FakeStateManager:
        def load_state(self, _key):
            return state

    class FakeCommandsV0:
        def __init__(self, **_kwargs):
            pass

        def cmd_review(self, *, path, ask_approve=True, test_diff_first=False, **_kwargs):
            calls.append(("review", (path, ask_approve, test_diff_first)))

    monkeypatch.setattr(review_cmd, "CommandsV0", FakeCommandsV0)

    context = SimpleNamespace(
        key="rid",
        state_manager=FakeStateManager(),
        config={"review": {"test_diff_first_default": True}},
    )
    args = SimpleNamespace(items=["a.py"], todo=False, skim=False, loc_lte=None, test_diff_first=None)

    review_cmd.impl(args=args, context=context)

    assert calls == [("review", ("a.py", True, True))]


def test_cmd_review_preview_approve_marks_reviewed_without_showing_full_diff(monkeypatch):
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"test_widget.py": FileState(lines=3)},
    )

    calls: list[tuple[str, object]] = []

    class FakeStateManager:
        def load_state(self, _key):
            return state

        def mark_file_reviewed(self, _state, path):
            calls.append(("mark", path))
            state.files[path].approved_sha = "newsha"

        def save_state(self, _state):
            calls.append(("save", ""))

    def fake_diff_filtered(path, *, diff_target, line_patterns):
        calls.append(("diff_filtered", (path, diff_target, tuple(line_patterns))))
        return 1

    def fake_diff(path, diff_target="main"):
        calls.append(("diff", (path, diff_target)))

    monkeypatch.setattr(commands_v0, "diff_filtered", fake_diff_filtered)
    monkeypatch.setattr(commands_v0, "diff", fake_diff)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    cmd = commands_v0.CommandsV0(
        key="rid",
        state_manager=FakeStateManager(),
        config={
            "review": {
                "test_file_patterns": ["^test_"],
                "test_diff_patterns": ["def[[:space:]]+test_"],
            }
        },
    )

    cmd.cmd_review("test_widget.py", ask_approve=True, test_diff_first=True)

    assert [c[0] for c in calls] == ["diff_filtered", "mark", "save"]


def test_diff_filtered_matches_assert_lines(monkeypatch, capsys):
    diff_text = """diff --git a/test_widget.py b/test_widget.py
--- a/test_widget.py
+++ b/test_widget.py
@@ -1,2 +1,3 @@
+def test_widget():
+    assert result
+    self.assertEqual(foo, bar)
"""

    def fake_run(args, **kwargs):
        if args[:3] == ["git", "diff", "main"]:
            return SimpleNamespace(stdout=diff_text, returncode=0)
        if args[:3] == ["grep", "-n", "-E"]:
            text = kwargs["input"]
            matches = []
            for idx, line in enumerate(text.splitlines(), start=1):
                if "assert" in line:
                    matches.append(f"{idx}:{line}")
            return SimpleNamespace(stdout="\n".join(matches) + ("\n" if matches else ""), returncode=0)
        raise AssertionError(f"Unexpected subprocess call: {args}")

    monkeypatch.setattr(git_source.subprocess, "run", fake_run)

    printed = git_source.diff_filtered(
        "test_widget.py",
        diff_target="main",
        line_patterns=["assert[A-Za-z_]*\\b"],
    )

    out = capsys.readouterr().out
    assert printed == 2
    assert "+    assert result" in out
    assert "+    self.assertEqual(foo, bar)" in out


def test_cmd_review_prompt_peek_opens_url_then_marks_reviewed(monkeypatch):
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"test_widget.py": FileState(lines=3)},
        metadata={"pr_url": "https://github.com/acme/repo/pull/123"},
    )

    calls: list[tuple[str, object]] = []

    class FakeStateManager:
        def load_state(self, _key):
            return state

        def mark_file_reviewed(self, _state, path):
            calls.append(("mark", path))
            state.files[path].approved_sha = "newsha"

        def save_state(self, _state):
            calls.append(("save", ""))

    def fake_diff(path, diff_target="main"):
        calls.append(("diff", (path, diff_target)))

    inputs = iter(["p", "y"])
    monkeypatch.setattr(commands_v0, "diff", fake_diff)
    monkeypatch.setattr(commands_v0, "open_url", lambda url: calls.append(("open", url)) or True)
    monkeypatch.setattr(
        commands_v0,
        "mark_reviewed_prompt",
        lambda **kwargs: prompt_impl(
            **kwargs,
            input_fn=lambda _prompt: next(inputs),
        ),
    )

    cmd = commands_v0.CommandsV0(
        key="rid",
        state_manager=FakeStateManager(),
        config={},
    )

    cmd.cmd_review("test_widget.py", ask_approve=True, test_diff_first=False)

    assert [c[0] for c in calls] == ["diff", "open", "mark", "save"]
