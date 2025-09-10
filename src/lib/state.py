import json
import os
from typing import Optional

from lib.models import FileState, PreApprovalBlock, ReviewState
from lib.sources.github import GHData

class StateManager:
    """Manages review state persistence in .git/acre directory"""
    
    def __init__(self, repo_root: str, current_sha: str):
        self.repo_root = repo_root
        self.current_sha = current_sha
        self.acre_dir = os.path.join(self.repo_root, ".git", "acre")
        os.makedirs(self.acre_dir, exist_ok=True)
    

    def state_file_path(self, review_id: str) -> str:
        """Get path to state file for given review ID"""
        return os.path.join(self.acre_dir, f"{review_id}.json")
    
    def save_state(self, state: ReviewState) -> None:
        """Save review state to disk"""
        state_dict = {
            "review_id": state.review_id,
            "init_commit_sha": state.init_commit_sha,
            "files": {
                path: {
                    "approved_sha": file_state.approved_sha,
                    "preapproved_sha": file_state.preapproved_sha,
                    "preapproved_blocks": [
                        {
                            "start_line": block.start_line,
                            "end_line": block.end_line,
                            "notes": block.notes
                        }
                        for block in file_state.preapproved_blocks
                    ],
                    "notes": file_state.notes,
                    "lines": file_state.lines
                }
                for path, file_state in state.files.items()
            },
            "notes": state.notes,
            "metadata": state.metadata
        }
        
        state_file = self.state_file_path(state.review_id)
        with open(state_file, "w") as f:
            json.dump(state_dict, f, indent=2)
    
    def load_state(self, review_id: str) -> Optional[ReviewState]:
        """Load review state from disk"""
        state_file = self.state_file_path(review_id)
        if not os.path.exists(state_file):
            return None
        
        with open(state_file) as f:
            data = json.load(f)
        
        files = {}
        for path, file_data in data.get("files", {}).items():
            preapproved_blocks = [
                PreApprovalBlock(
                    start_line=block["start_line"],
                    end_line=block["end_line"],
                    notes=block.get("notes", "")
                )
                for block in file_data.get("preapproved_blocks", [])
            ]
            
            files[path] = FileState(
                approved_sha=file_data.get("approved_sha"),
                preapproved_sha=file_data.get("preapproved_sha"),
                preapproved_blocks=preapproved_blocks,
                notes=file_data.get("notes", ""),
                lines=file_data.get("lines", 0)
            )
        
        return ReviewState(
            review_id=data["review_id"],
            init_commit_sha=data["init_commit_sha"],
            files=files,
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {})
        )
    
    def initialize_review(self, review_id: str, gh_data: Optional[GHData] = None) -> ReviewState:
        """Initialize a new review state"""
        files = {}
        
        # Populate files from GitHub data if available
        if gh_data:
            for file_path in gh_data.files:
                lines_changed = gh_data.lines_changed.get(file_path, 0)
                files[file_path] = FileState(lines=lines_changed)
        
        state = ReviewState(
            review_id=review_id,
            init_commit_sha=self.current_sha,
            files=files,
        )

        if gh_data:
            if gh_data.base_commit:
                state.metadata["base_commit"] = gh_data.base_commit
            if gh_data.head_commit:
                state.metadata["head_commit"] = gh_data.head_commit
        
        self.save_state(state)
        return state

    def do_reset(self, state: ReviewState):
        for k in state.files.keys():
            state.files[k].do_reset()

    def mark_file_reviewed(self, state: ReviewState, path: str):
        f = state.files[path]
        if f is None:
            raise Exception(f"Not found for approval: {f}")
        f.approved_sha = self.current_sha
