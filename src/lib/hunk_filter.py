from __future__ import annotations

import re
from typing import List


_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _strip_ansi(s: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", s)


def filter_diff_hunks_by_regex(
    diff_lines: List[str],
    *,
    pattern: str,
    include_context: bool = False,
) -> List[str]:
    """
    Filters a single-file `git diff` output to include only hunks where at least
    one relevant line matches `pattern`. If any line in a hunk matches, the whole
    hunk is included.

    By default, only changed lines (`+`/`-`) are considered for matching; pass
    `include_context=True` to also consider context lines (leading space).
    """
    if not diff_lines:
        return diff_lines

    rx = re.compile(pattern)

    header: list[str] = []
    hunks: list[list[str]] = []

    current_hunk: list[str] | None = None
    saw_hunk = False

    for line in diff_lines:
        if _strip_ansi(line).startswith("@@"):
            saw_hunk = True
            if current_hunk is not None:
                hunks.append(current_hunk)
            current_hunk = [line]
            continue

        if current_hunk is None:
            header.append(line)
        else:
            current_hunk.append(line)

    if current_hunk is not None:
        hunks.append(current_hunk)

    if not saw_hunk:
        # Binary diffs / mode-only changes don't have hunks; don't hide them.
        return diff_lines

    def line_is_matchable(hunk_line: str) -> bool:
        if not hunk_line:
            return False
        stripped = _strip_ansi(hunk_line)
        if stripped.startswith(("+++ ", "--- ")):
            return False
        if stripped[0] in {"+", "-"}:
            return True
        if include_context and stripped[0] == " ":
            return True
        return False

    kept: list[list[str]] = []
    for hunk in hunks:
        matched = any(
            rx.search(_strip_ansi(hunk_line)[1:].rstrip("\n")) is not None
            for hunk_line in hunk
            if line_is_matchable(hunk_line)
        )
        if matched:
            kept.append(hunk)

    if not kept:
        return []

    out: list[str] = []
    out.extend(header)
    for hunk in kept:
        out.extend(hunk)
    return out
