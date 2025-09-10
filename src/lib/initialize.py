import sys
from typing import Optional

from lib.review_identifier import ReviewIdentifier
from lib.sources.github import data_from_gh
from lib.state import StateManager
from lib.commit_range import CommitRangeNormalizer


def cmd_init(state_manager: StateManager, review_id: Optional[str] = None, force: bool = False,
             commit: Optional[str] = None, from_ref: Optional[str] = None, to_ref: Optional[str] = None) -> None:
    """Initialize a new code review session"""
    try:
        # Normalize commit range options
        commit_range = CommitRangeNormalizer.normalize(commit=commit, from_ref=from_ref, to_ref=to_ref)
        
        if not review_id:
            review_id = ReviewIdentifier.determine_review_id(commit_range=commit_range)
        
        if not force:
            # Check if review already exists
            existing_state = state_manager.load_state(review_id)
            if existing_state:
                print(f"Review '{review_id}' already exists")
                print(f"Initialized at commit: {existing_state.init_commit_sha}")
                return
        
        # Get GitHub data for initial files and line counts
        # TODO: For commit ranges, we should get diffs from the range instead of current GitHub data
        gh_data = data_from_gh()
        
        # Initialize new review with GitHub data
        state = state_manager.initialize_review(review_id, gh_data)
        
        print(f"Initialized review: {review_id}")
        if commit_range:
            print(f"Commit range: {commit_range.from_sha[:8]}..{commit_range.to_sha[:8]}")
        print(f"Commit SHA: {state.init_commit_sha}")
        print(f"State saved to: {state_manager.state_file_path(review_id)}")
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
