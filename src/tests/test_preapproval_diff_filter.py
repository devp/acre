def test_filter_diff_lines_excludes_preapproved_blocks():
    # Diff "line numbers" here refer to the rendered diff output for a single file,
    # not source-file line numbers.
    diff_lines = [
        "diff --git a/x b/x\n",
        "--- a/x\n",
        "+++ b/x\n",
        "@@ -1,1 +1,2 @@\n",
        "-old\n",
        "+new\n",
        "+more\n",
    ]

    from lib.diff_filter import filter_diff_lines  # noqa: PLC0415
    from lib.models import PreApprovalBlock  # noqa: PLC0415

    filtered = filter_diff_lines(
        diff_lines,
        preapproved_blocks=[PreApprovalBlock(start_line=5, end_line=6)],
    )

    assert filtered == [
        "diff --git a/x b/x\n",
        "--- a/x\n",
        "+++ b/x\n",
        "@@ -1,1 +1,2 @@\n",
        "+more\n",
    ]


def test_filter_diff_lines_keeps_everything_when_no_blocks():
    diff_lines = ["a\n", "b\n", "c\n"]

    from lib.diff_filter import filter_diff_lines  # noqa: PLC0415

    assert filter_diff_lines(diff_lines, preapproved_blocks=[]) == diff_lines
