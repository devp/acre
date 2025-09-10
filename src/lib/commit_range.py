from typing import Optional
from dataclasses import dataclass

from lib.sources.git import resolve_ref, get_commit_parent, get_current_commit_sha


@dataclass
class CommitRange:
    """Represents a normalized commit range"""
    from_sha: str
    to_sha: str
    
    def to_review_id(self) -> str:
        """Generate a review identifier for this commit range"""
        # Truncate SHAs to 8 characters for readability
        from_short = self.from_sha[:8]
        to_short = self.to_sha[:8]
        return f"commit-range-{from_short}-to-{to_short}"


class CommitRangeNormalizer:
    """Normalizes commit range options into a standard format"""
    
    @staticmethod
    def normalize(commit: Optional[str] = None, 
                  from_ref: Optional[str] = None, 
                  to_ref: Optional[str] = None) -> Optional[CommitRange]:
        """
        Normalize commit range options into a CommitRange object.
        
        Args:
            commit: Specific commit to review (shows commit vs commit~1)
            from_ref: Start of range (shows from_ref to to_ref or HEAD)
            to_ref: End of range (defaults to HEAD if from_ref specified)
            
        Returns:
            CommitRange object or None if no range specified
            
        Raises:
            ValueError: If invalid combinations or git refs are provided
        """
        # Validate mutually exclusive options
        if commit and (from_ref or to_ref):
            raise ValueError("--commit cannot be used with --from or --to")
            
        # Handle --commit option
        if commit:
            try:
                commit_sha = resolve_ref(commit)
                parent_sha = get_commit_parent(commit_sha)
                return CommitRange(from_sha=parent_sha, to_sha=commit_sha)
            except ValueError as e:
                raise ValueError(f"Invalid commit reference '{commit}': {e}")
        
        # Handle --from option
        if from_ref:
            try:
                from_sha = resolve_ref(from_ref)
                
                if to_ref:
                    to_sha = resolve_ref(to_ref)
                else:
                    # Default to HEAD
                    to_sha = get_current_commit_sha()
                    
                return CommitRange(from_sha=from_sha, to_sha=to_sha)
            except ValueError as e:
                raise ValueError(f"Invalid reference: {e}")
        
        # Handle --to without --from (invalid)
        if to_ref:
            raise ValueError("--to requires --from to be specified")
            
        return None