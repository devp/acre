import json
import subprocess
from typing import Optional

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
