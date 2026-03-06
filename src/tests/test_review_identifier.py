import pytest

import lib.review_identifier as review_identifier


def test_review_identifier_from_branch_normalizes_slash(monkeypatch):
    monkeypatch.setattr(review_identifier, "get_current_branch", lambda: "feature/foo")
    monkeypatch.setattr(review_identifier, "get_name_rev", lambda: "ignored")
    assert review_identifier.ReviewIdentifier.from_branch() == "branch-feature-foo"


def test_review_identifier_from_branch_ignores_head(monkeypatch):
    monkeypatch.setattr(review_identifier, "get_current_branch", lambda: "")
    monkeypatch.setattr(review_identifier, "get_name_rev", lambda: "HEAD")
    assert review_identifier.ReviewIdentifier.from_branch() is None


def test_review_identifier_determine_review_id_prefers_branch_over_commit(monkeypatch):
    monkeypatch.setattr(review_identifier.ReviewIdentifier, "from_branch", staticmethod(lambda: "branch-x"))
    monkeypatch.setattr(review_identifier.ReviewIdentifier, "from_commit", staticmethod(lambda: "commit-y"))
    assert review_identifier.ReviewIdentifier.determine_review_id() == "branch-x"


def test_review_identifier_determine_review_id_falls_back_to_commit(monkeypatch):
    monkeypatch.setattr(review_identifier.ReviewIdentifier, "from_branch", staticmethod(lambda: None))
    monkeypatch.setattr(review_identifier.ReviewIdentifier, "from_commit", staticmethod(lambda: "commit-y"))
    assert review_identifier.ReviewIdentifier.determine_review_id() == "commit-y"


def test_review_identifier_determine_review_id_raises_when_no_sources(monkeypatch):
    monkeypatch.setattr(review_identifier.ReviewIdentifier, "from_branch", staticmethod(lambda: None))
    monkeypatch.setattr(review_identifier.ReviewIdentifier, "from_commit", staticmethod(lambda: None))
    with pytest.raises(ValueError, match="Unable to determine review identifier"):
        review_identifier.ReviewIdentifier.determine_review_id()

