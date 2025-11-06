import argparse

from cli.context import Context
from lib.initialize import cmd_init


def impl(args: argparse.Namespace, context: Context):
    cmd_init(
        state_manager=context.state_manager,
        review_id=args.review_id,
        force=args.force,
        git_range=getattr(args, 'git_range', None),
    )


def register(sub: argparse._SubParsersAction):
    cmd = sub.add_parser("init", help="Initialize a new code review session")
    cmd.add_argument("--review-id", help="Custom review identifier")
    cmd.add_argument("--force", help="Overwrite existing state file", action="store_true")
    cmd.add_argument("--git-range", help="Git range to use for diff (e.g., main..HEAD, commit1..commit2)")
    cmd.set_defaults(impl=impl)
