from typing import Optional

from lib.sources.git import get_current_branch, get_current_commit_sha, get_name_rev

class ReviewIdentifier:
    """Modular logic for determining review slug/identifier"""
    
    @staticmethod
    def from_branch() -> Optional[str]:
        """Get identifier from current branch"""
        try:
            branch_name = get_current_branch() or get_name_rev()
            if branch_name and branch_name != "HEAD":
                # Normalize branch name by replacing "/" with "-"
                normalized_branch_name = branch_name.replace("/", "-")
                return f"branch-{normalized_branch_name}"
        except ValueError:
            pass
        return None
    
    @staticmethod
    def from_commit() -> Optional[str]:
        """Get identifier from current commit"""
        try:
            commit_sha = get_current_commit_sha()
            if commit_sha:
                return f"commit-{commit_sha}"
        except ValueError:
            pass
        return None
    
    @classmethod
    def determine_review_id(cls) -> str:
        """Determine review ID using fallback strategy"""
        if branch_id := cls.from_branch():
            return branch_id

        if commit_id := cls.from_commit():
            return commit_id
        
        raise ValueError("Unable to determine review identifier")
