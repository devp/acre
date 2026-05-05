from lib.models import PreApprovalBlock


def excluded_diff_line_numbers(preapproved_blocks: list[PreApprovalBlock]) -> set[int]:
    excluded: set[int] = set()
    for block in preapproved_blocks:
        for i in range(block.start_line, block.end_line + 1):
            excluded.add(i)
    return excluded


def filter_diff_lines(
    lines: list[str],
    preapproved_blocks: list[PreApprovalBlock],
) -> list[str]:
    if not preapproved_blocks:
        return list(lines)
    excluded = excluded_diff_line_numbers(preapproved_blocks)
    return [line for idx, line in enumerate(lines, start=1) if idx not in excluded]
