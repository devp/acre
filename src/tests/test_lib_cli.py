from lib.cli import CommandOptions, Commands, parse_args_from_cli


def test_parse_overview():
    v = parse_args_from_cli(["overview"])
    assert v
    assert v.command == Commands.OVERVIEW


def test_parse_deep_review():
    v = parse_args_from_cli(["review", "--deep", "file.txt"])
    assert v
    assert v.command == Commands.REVIEW
    assert CommandOptions.REVIEW_DEEP in v.options
