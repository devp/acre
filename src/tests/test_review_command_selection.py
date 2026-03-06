from types import SimpleNamespace

import lib.commands.review as review_cmd
from lib.models import FileState, ReviewState


def test_select_paths_to_review_resolves_numeric_indexes_to_paths():
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"a.py": FileState(), "b.py": FileState(), "c.py": FileState()},
    )
    known_files = ["a.py", "b.py", "c.py"]
    assert (
        review_cmd._select_paths_to_review(
            known_files=known_files,
            state=state,
            items=["2", "3"],
            todo=False,
            loc_lte=None,
        )
        == ["b.py", "c.py"]
    )


def test_select_paths_to_review_supports_explicit_paths():
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"a.py": FileState(), "b.py": FileState(), "c.py": FileState()},
    )
    known_files = ["a.py", "b.py", "c.py"]
    assert (
        review_cmd._select_paths_to_review(
            known_files=known_files,
            state=state,
            items=["c.py", "a.py"],
            todo=False,
            loc_lte=None,
        )
        == ["c.py", "a.py"]
    )


def test_select_paths_to_review_todo_filters_already_reviewed_files():
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={
            "a.py": FileState(approved_sha="sha"),
            "b.py": FileState(approved_sha=None),
        },
    )
    known_files = ["a.py", "b.py"]
    assert (
        review_cmd._select_paths_to_review(
            known_files=known_files,
            state=state,
            items=None,
            todo=True,
            loc_lte=None,
        )
        == ["b.py"]
    )


def test_select_paths_to_review_loc_lte_filters_by_lines_changed():
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"a.py": FileState(lines=5), "b.py": FileState(lines=100)},
    )
    known_files = ["a.py", "b.py"]
    assert (
        review_cmd._select_paths_to_review(
            known_files=known_files,
            state=state,
            items=None,
            todo=False,
            loc_lte=10,
        )
        == ["a.py"]
    )


def test_review_impl_skim_mode_approves_all_when_confirmed(monkeypatch):
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={"a.py": FileState(), "b.py": FileState()},
    )
    calls: list[tuple[str, str]] = []

    class FakeStateManager:
        def load_state(self, _key):
            return state

        def mark_file_reviewed(self, state, path):
            calls.append(("mark", path))
            state.files[path].approved_sha = "newsha"

        def save_state(self, _state):
            calls.append(("save", ""))

    class FakeCommandsV0:
        def __init__(self, **_kwargs):
            pass

        def cmd_review(self, *, path, ask_approve=True, **_kwargs):
            calls.append(("review", f"{path}:{ask_approve}"))

    monkeypatch.setattr(review_cmd, "CommandsV0", FakeCommandsV0)
    monkeypatch.setattr(review_cmd, "yn", lambda _prompt: True)

    context = SimpleNamespace(key="rid", state_manager=FakeStateManager(), config={})
    args = SimpleNamespace(items=[], todo=False, skim=True, loc_lte=None)

    review_cmd.impl(args=args, context=context)

    assert ("review", "a.py:False") in calls
    assert ("review", "b.py:False") in calls
    assert ("mark", "a.py") in calls
    assert ("mark", "b.py") in calls
    assert ("save", "") in calls

