import re


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def filter_diff_hunks_by_regex(
    lines: list[str],
    pattern: str,
    include_context: bool = False,
) -> list[str]:
    """Return only the diff hunks that contain a changed line matching pattern.

    Preamble lines (before the first @@) are included only when at least one
    hunk matches.  Context lines are ignored unless include_context is True.
    """
    compiled = re.compile(pattern)

    preamble: list[str] = []
    hunks: list[list[str]] = []
    current_hunk: list[str] = []

    for line in lines:
        if _strip_ansi(line).startswith("@@"):
            if current_hunk:
                hunks.append(current_hunk)
            current_hunk = [line]
        elif not current_hunk:
            preamble.append(line)
        else:
            current_hunk.append(line)
    if current_hunk:
        hunks.append(current_hunk)

    matching: list[list[str]] = []
    for hunk in hunks:
        for line in hunk[1:]:  # skip the @@ header itself
            stripped = _strip_ansi(line)
            is_changed = stripped.startswith("+") or stripped.startswith("-")
            is_context = not is_changed
            if is_changed or (include_context and is_context):
                if compiled.search(stripped):
                    matching.append(hunk)
                    break

    if not matching:
        return []
    return preamble + [line for hunk in matching for line in hunk]
