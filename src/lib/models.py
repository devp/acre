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

    def do_reset(self):
        self.approved_sha = None
        self.preapproved_sha = None
        self.preapproved_blocks = []
        self.notes = None


@dataclass
class ReviewState:
    review_id: str
    init_commit_sha: str
    files: Dict[str, FileState] = field(default_factory=dict)
    notes: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def total_lines(self):
        return sum([f.lines for f in self.files.values()])

    def total_reviewed_lines(self):
        return sum([f.lines for f in self.files.values() if f.approved_sha])

    def reviewed_files(self) -> Dict[str, FileState]:
        return {k: f for (k, f) in self.files.items() if f.approved_sha}

    def lines_of_file(self, file_name: str) -> int | None:
        f = self.files.get(file_name)
        return f.lines if f is not None else None

    def is_file_reviewed(self, file_name: str) -> bool | None:
        f = self.files.get(file_name)
        return bool(f.approved_sha) if f is not None else None

    def diff_target(self) -> str:
        a = self.metadata.get("base_commit")
        b = self.metadata.get("head_commit")
        if a and b:
            return f"{a}..{b}"
        return "main"

    def __getitem__(self, key):
        """Primarily for legacy support."""
        match key:
            case 'total_lines':
                return self.total_lines()
            case 'files':
                return self.files
