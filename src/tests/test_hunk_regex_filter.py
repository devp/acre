from __future__ import annotations


def test_filter_diff_hunks_by_regex_includes_whole_hunk_when_changed_line_matches():
    diff_lines = [
        "diff --git a/x b/x\n",
        "--- a/x\n",
        "+++ b/x\n",
        "@@ -1,2 +1,2 @@\n",
        "-old thing\n",
        "+new thing\n",
        " context\n",
        "@@ -10,2 +10,2 @@\n",
        "-foo\n",
        "+bar\n",
    ]

    from lib.hunk_filter import filter_diff_hunks_by_regex  # noqa: PLC0415

    filtered = filter_diff_hunks_by_regex(diff_lines, pattern=r"new")

    assert filtered == [
        "diff --git a/x b/x\n",
        "--- a/x\n",
        "+++ b/x\n",
        "@@ -1,2 +1,2 @@\n",
        "-old thing\n",
        "+new thing\n",
        " context\n",
    ]


def test_filter_diff_hunks_by_regex_ignores_context_lines_by_default():
    diff_lines = [
        "diff --git a/x b/x\n",
        "--- a/x\n",
        "+++ b/x\n",
        "@@ -1,1 +1,1 @@\n",
        "-old\n",
        "+new\n",
        " context-match-me\n",
    ]

    from lib.hunk_filter import filter_diff_hunks_by_regex  # noqa: PLC0415

    assert filter_diff_hunks_by_regex(diff_lines, pattern=r"match-me") == []


def test_filter_diff_hunks_by_regex_can_include_context_lines():
    diff_lines = [
        "diff --git a/x b/x\n",
        "--- a/x\n",
        "+++ b/x\n",
        "@@ -1,1 +1,1 @@\n",
        "-old\n",
        "+new\n",
        " context-match-me\n",
    ]

    from lib.hunk_filter import filter_diff_hunks_by_regex  # noqa: PLC0415

    assert filter_diff_hunks_by_regex(
        diff_lines, pattern=r"match-me", include_context=True
    ) == diff_lines

