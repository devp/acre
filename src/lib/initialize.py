import sys
from typing import Optional

from lib.review_identifier import ReviewIdentifier
from lib.sources.git import data_from_git_range
from lib.sources.github import data_from_gh
from lib.state import StateManager


def cmd_init(state_manager: StateManager, review_id: Optional[str] = None, force: bool = False, git_range: Optional[str] = None) -> None:
    """Initialize a new code review session"""
    try:
        if not review_id:
            review_id = ReviewIdentifier.determine_review_id()
        
        if not force:
            # Check if review already exists
            existing_state = state_manager.load_state(review_id)
            if existing_state:
                print(f"Review '{review_id}' already exists")
                print(f"Initialized at commit: {existing_state.init_commit_sha}")
                return
        
        # Get data for initial files and line counts
        if git_range:
            gh_data = data_from_git_range(git_range)
            print(f"Using git range: {git_range}")
        else:
            gh_data = data_from_gh()
        
        # Initialize new review with data
        state = state_manager.initialize_review(review_id, gh_data)
        
        print(f"Initialized review: {review_id}")
        print(f"Commit SHA: {state.init_commit_sha}")
        print(f"State saved to: {state_manager.state_file_path(review_id)}")
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
