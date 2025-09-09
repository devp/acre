import re
from typing import Optional

from lib.sources.git import get_current_branch
from lib.sources.github import GHData


def find_jira_tag(data: GHData):
    def _find(text: Optional[str]):
        if text:
            m = re.search(r"[A-Z][A-Z0-9]+-\d+", text or "")
            return m.group(0) if m else None
    return (
        _find(data.title) or
        _find(data.body) or
        _find(get_current_branch())
    )
