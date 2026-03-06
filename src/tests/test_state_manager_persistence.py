from lib.models import FileState, PreApprovalBlock, ReviewState
from lib.sources.git import GitData
from lib.state import StateManager


def test_state_manager_save_load_roundtrip(tmp_path):
    repo_root = str(tmp_path)
    state_manager = StateManager(repo_root=repo_root, current_sha="deadbeef")

    state = ReviewState(
        review_id="r1",
        init_commit_sha="initsha",
        files={
            "a.py": FileState(
                approved_sha="approved1",
                preapproved_sha="pre1",
                preapproved_blocks=[PreApprovalBlock(start_line=1, end_line=3, notes="n1")],
                notes="file-notes",
                lines=10,
            ),
            "b.py": FileState(lines=5),
        },
        notes="review-notes",
        metadata={"base_commit": "base", "head_commit": "head", "pr_number": "123"},
    )

    state_manager.save_state(state)
    loaded = state_manager.load_state("r1")

    assert loaded is not None
    assert loaded.review_id == "r1"
    assert loaded.init_commit_sha == "initsha"
    assert loaded.notes == "review-notes"
    assert loaded.metadata == {"base_commit": "base", "head_commit": "head", "pr_number": "123"}

    assert set(loaded.files.keys()) == {"a.py", "b.py"}
    assert loaded.files["a.py"].approved_sha == "approved1"
    assert loaded.files["a.py"].preapproved_sha == "pre1"
    assert loaded.files["a.py"].notes == "file-notes"
    assert loaded.files["a.py"].lines == 10
    assert [(b.start_line, b.end_line, b.notes) for b in loaded.files["a.py"].preapproved_blocks] == [
        (1, 3, "n1")
    ]
    assert loaded.files["b.py"].approved_sha is None
    assert loaded.files["b.py"].lines == 5


def test_state_manager_initialize_review_seeds_files_and_metadata(tmp_path):
    repo_root = str(tmp_path)
    state_manager = StateManager(repo_root=repo_root, current_sha="c0ffee")

    gh_data = GitData(
        title="t",
        body="b",
        number=7,
        files=["a.py", "b.py"],
        lines_changed={"a.py": 3, "b.py": 0},
        base_commit="base",
        head_commit="head",
    )

    state = state_manager.initialize_review("rid", gh_data=gh_data)
    assert state.review_id == "rid"
    assert state.init_commit_sha == "c0ffee"
    assert set(state.files.keys()) == {"a.py", "b.py"}
    assert state.files["a.py"].lines == 3
    assert state.files["b.py"].lines == 0
    assert state.metadata == {"base_commit": "base", "head_commit": "head", "pr_number": "7"}

    loaded = state_manager.load_state("rid")
    assert loaded is not None
    assert loaded.metadata == {"base_commit": "base", "head_commit": "head", "pr_number": "7"}


def test_state_manager_mark_file_reviewed_and_reset(tmp_path):
    repo_root = str(tmp_path)
    state_manager = StateManager(repo_root=repo_root, current_sha="newsha")

    state = ReviewState(
        review_id="rid",
        init_commit_sha="initsha",
        files={
            "a.py": FileState(
                approved_sha=None,
                preapproved_sha="pre",
                preapproved_blocks=[PreApprovalBlock(start_line=1, end_line=1)],
                notes="n",
                lines=1,
            )
        },
    )

    state_manager.mark_file_reviewed(state, "a.py")
    assert state.files["a.py"].approved_sha == "newsha"

    state_manager.do_reset(state)
    assert state.files["a.py"].approved_sha is None
    assert state.files["a.py"].preapproved_sha is None
    assert state.files["a.py"].preapproved_blocks == []
    assert state.files["a.py"].notes is None

