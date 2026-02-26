from __future__ import annotations

from typing import Iterable, List

from lib.models import PreApprovalBlock


def filter_diff_lines(
    diff_lines: List[str],
    *,
    preapproved_blocks: Iterable[PreApprovalBlock],
) -> List[str]:
    """
    Filter rendered diff lines by removing any 1-based line ranges referenced
    by `preapproved_blocks`.
    """
    if not diff_lines:
        return diff_lines

    excluded: set[int] = set()
    for block in preapproved_blocks:
        start = max(1, block.start_line)
        end = max(start, block.end_line)
        excluded.update(range(start, end + 1))

    if not excluded:
        return diff_lines

    return [line for idx, line in enumerate(diff_lines, start=1) if idx not in excluded]

