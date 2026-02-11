from types import SimpleNamespace

import lib.commands.review as review_cmd
import lib.commands_v0 as commands_v0
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
                "test_diff_patterns": ["def[[:space:]]+test_"],
            }
        },
    )

    cmd.cmd_review("test_widget.py", ask_approve=False, test_diff_first=True)

    assert [c[0] for c in calls] == ["diff_filtered", "diff"]


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
