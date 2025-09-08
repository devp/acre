import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PreApprovalBlock:
    start_line: int
    end_line: int
    notes: Optional[str] = None


@dataclass
class FileState:
    approved_sha: Optional[str] = None
    preapproved_sha: Optional[str] = None
    preapproved_blocks: List[PreApprovalBlock] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class ReviewState:
    review_id: str
    init_commit_sha: str
    files: Dict[str, FileState] = field(default_factory=dict)
    notes: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


class ReviewIdentifier:
    """Modular logic for determining review slug/identifier"""
    
    @staticmethod
    def from_pr() -> Optional[str]:
        """Get identifier from current PR"""
        try:
            pr_result = subprocess.run(
                ["gh", "pr", "view", "--json", "number"],
                check=True,
                capture_output=True,
                text=True,
            )
            pr_data = json.loads(pr_result.stdout)
            pr_number = pr_data.get("number")
            return f"pr-{pr_number}" if pr_number else None
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None
    
    @staticmethod
    def from_branch() -> Optional[str]:
        """Get identifier from current branch"""
        try:
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            branch_name = branch_result.stdout.strip()
            if branch_name and branch_name != "HEAD":
                # Normalize branch name by replacing "/" with "-" for filesystem compatibility
                normalized_branch_name = branch_name.replace("/", "-")
                return f"branch-{normalized_branch_name}"
            return None
        except subprocess.CalledProcessError:
            return None
    
    @staticmethod
    def from_commit() -> Optional[str]:
        """Get identifier from current commit"""
        try:
            commit_result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = commit_result.stdout.strip()
            return f"commit-{commit_sha}" if commit_sha else None
        except subprocess.CalledProcessError:
            return None
    
    @classmethod
    def determine_review_id(cls) -> str:
        """Determine review ID using fallback strategy"""
        # Try PR first (preferred)
        pr_id = cls.from_pr()
        if pr_id:
            return pr_id
        
        # Fall back to branch name
        branch_id = cls.from_branch()
        if branch_id:
            return branch_id
        
        # Final fallback to commit
        commit_id = cls.from_commit()
        if commit_id:
            return commit_id
        
        raise ValueError("Unable to determine review identifier")


class StateManager:
    """Manages review state persistence in .git/acre directory"""
    
    def __init__(self):
        self.repo_root = self._get_repo_root()
        self.acre_dir = os.path.join(self.repo_root, ".git", "acre")
        os.makedirs(self.acre_dir, exist_ok=True)
    
    def _get_repo_root(self) -> str:
        """Get repository root directory"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            raise ValueError("Not in a git repository")
    
    def _get_current_commit_sha(self) -> str:
        """Get current commit SHA"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            raise ValueError("Unable to get current commit SHA")
    
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
                    "notes": file_state.notes
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
                notes=file_data.get("notes", "")
            )
        
        return ReviewState(
            review_id=data["review_id"],
            init_commit_sha=data["init_commit_sha"],
            files=files,
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {})
        )
    
    def initialize_review(self, review_id: Optional[str] = None) -> ReviewState:
        """Initialize a new review state"""
        if not review_id:
            review_id = ReviewIdentifier.determine_review_id()
        
        current_sha = self._get_current_commit_sha()
        
        state = ReviewState(
            review_id=review_id,
            init_commit_sha=current_sha
        )
        
        self.save_state(state)
        return state


def cmd_init(review_id: Optional[str] = None) -> None:
    """Initialize a new code review session"""
    try:
        state_manager = StateManager()
        
        if not review_id:
            review_id = ReviewIdentifier.determine_review_id()
        
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
