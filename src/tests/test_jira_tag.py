import lib.sources.jira as jira
from lib.sources.git import GitData


def test_find_jira_tag_prefers_title_then_body_then_branch(monkeypatch):
    monkeypatch.setattr(jira, "get_current_branch", lambda: "ABC-3-branch")
    data = GitData(title="ABC-1 title", body="ABC-2 body")
    assert jira.find_jira_tag(data) == "ABC-1"


def test_find_jira_tag_falls_back_to_body(monkeypatch):
    monkeypatch.setattr(jira, "get_current_branch", lambda: "ABC-3-branch")
    data = GitData(title="no ticket", body="ABC-2 body")
    assert jira.find_jira_tag(data) == "ABC-2"


def test_find_jira_tag_falls_back_to_branch(monkeypatch):
    monkeypatch.setattr(jira, "get_current_branch", lambda: "ABC-3-branch")
    data = GitData(title="no ticket", body="no ticket")
    assert jira.find_jira_tag(data) == "ABC-3"

