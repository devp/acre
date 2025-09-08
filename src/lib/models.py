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
    lines: int = 0  # Number of changed lines (additions + deletions)


@dataclass
class ReviewState:
    review_id: str
    init_commit_sha: str
    files: Dict[str, FileState] = field(default_factory=dict)
    notes: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
