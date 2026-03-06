from lib.models import FileState, ReviewState


def test_review_state_helpers_totals_and_flags():
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={
            "a.py": FileState(lines=3, approved_sha="sha1"),
            "b.py": FileState(lines=5, approved_sha=None),
        },
    )

    assert state.total_lines() == 8
    assert state.total_reviewed_lines() == 3
    assert set(state.reviewed_files().keys()) == {"a.py"}
    assert state.is_file_reviewed("a.py") is True
    assert state.is_file_reviewed("b.py") is False
    assert state.is_file_reviewed("missing.py") is None
    assert state.lines_of_file("a.py") == 3
    assert state.lines_of_file("missing.py") is None


def test_review_state_diff_target_prefers_base_head_metadata():
    state = ReviewState(
        review_id="rid",
        init_commit_sha="init",
        files={},
        metadata={"base_commit": "abc", "head_commit": "def"},
    )
    assert state.diff_target() == "abc..def"


def test_review_state_diff_target_defaults_to_main():
    state = ReviewState(review_id="rid", init_commit_sha="init", files={}, metadata={})
    assert state.diff_target() == "main"

