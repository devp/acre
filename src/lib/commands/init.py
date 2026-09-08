import argparse

from cli.context import Context
from lib.initialize import cmd_init


def impl(args: argparse.Namespace, context: Context):
    git_commit = getattr(args, 'git_commit', None)
    if getattr(args, 'upbranch', False):
        git_range = "upbranch"
    elif git_commit:
        git_range = f"{git_commit}~1..{git_commit}"
    else:
        git_range = getattr(args, 'git_range', None)
    cmd_init(
        state_manager=context.state_manager,
        review_id=args.review_id,
        force=args.force,
        git_range=git_range,
    )


def register(sub: argparse._SubParsersAction):
    cmd = sub.add_parser("init", help="Initialize a new code review session")
    cmd.add_argument("--review-id", help="Custom review identifier")
    cmd.add_argument("--force", help="Overwrite existing state file", action="store_true")
    range_group = cmd.add_mutually_exclusive_group()
    range_group.add_argument(
        "--git-range",
        help="Git range to use for diff (e.g., main..HEAD, commit1..commit2, or 'upbranch')",
    )
    range_group.add_argument(
        "--upbranch",
        action="store_true",
        help="Shortcut for --git-range upbranch: diff from where this branch diverged from the default branch",
    )
    range_group.add_argument(
        "--git-commit",
        help="Shortcut for --git-range <commit>~1..<commit>: diff a single commit against its parent",
    )
    cmd.set_defaults(impl=impl)
