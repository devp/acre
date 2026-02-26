from __future__ import annotations


def test_state_manager_can_add_preapproved_block(tmp_path):
    # Minimal fake repo root that still exercises on-disk persistence.
    (tmp_path / ".git").mkdir()

    from lib.models import FileState, ReviewState  # noqa: PLC0415
    from lib.state import StateManager  # noqa: PLC0415

    state = ReviewState(
        review_id="r1",
        init_commit_sha="initsha",
        files={"f.py": FileState(lines=1)},
    )

    mgr = StateManager(repo_root=str(tmp_path), current_sha="headsha")
    mgr.save_state(state)

    mgr.add_preapproved_block(state, path="f.py", start_line=10, end_line=12, notes="skip")
    mgr.save_state(state)

    loaded = mgr.load_state("r1")
    assert loaded is not None
    blocks = loaded.files["f.py"].preapproved_blocks
    assert len(blocks) == 1
    assert blocks[0].start_line == 10
    assert blocks[0].end_line == 12
    assert blocks[0].notes == "skip"

