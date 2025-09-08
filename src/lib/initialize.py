import sys
from typing import Optional

from lib.review_identifier import ReviewIdentifier
from lib.state import StateManager


def cmd_init(review_id: Optional[str] = None, force: bool = False) -> None:
    """Initialize a new code review session"""
    try:
        state_manager = StateManager()
        
        if not review_id:
            review_id = ReviewIdentifier.determine_review_id()
        
        if not force:
            # Check if review already exists
            existing_state = state_manager.load_state(review_id)
            if existing_state:
                print(f"Review '{review_id}' already exists")
                print(f"Initialized at commit: {existing_state.init_commit_sha}")
                return
        
        # Initialize new review
        state = state_manager.initialize_review(review_id)
        
        print(f"Initialized review: {review_id}")
        print(f"Commit SHA: {state.init_commit_sha}")
        print(f"State saved to: {state_manager.state_file_path(review_id)}")
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
