import lib.initialize as initialize
from lib.sources.git import GitData
from lib.state import StateManager


def test_cmd_init_resolves_upbranch_before_diffing(monkeypatch, git_repo):
    monkeypatch.setattr(initialize, "resolve_upbranch_range", lambda: "deadbeef..HEAD")

    seen_ranges = []

    def fake_data_from_git_range(git_range):
        seen_ranges.append(git_range)
        return GitData(files=["a.py"], lines_changed={"a.py": 3}, base_commit="deadbeef", head_commit="head")

    monkeypatch.setattr(initialize, "data_from_git_range", fake_data_from_git_range)

    state_manager = StateManager(repo_root=str(git_repo), current_sha="head")
    initialize.cmd_init(state_manager=state_manager, review_id="rid", git_range="upbranch")

    assert seen_ranges == ["deadbeef..HEAD"]
    state = state_manager.load_state("rid")
    assert state is not None
    assert state.metadata["base_commit"] == "deadbeef"
