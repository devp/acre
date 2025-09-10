import argparse

from cli.context import Context
from lib.initialize import cmd_init


def impl(args: argparse.Namespace, context: Context):
    cmd_init(
        state_manager=context.state_manager,
        review_id=args.review_id,
        force=args.force,
        commit=getattr(args, 'commit', None),
        from_ref=getattr(args, 'from_ref', None),
        to_ref=getattr(args, 'to_ref', None),
    )


def register(sub: argparse._SubParsersAction):
    cmd = sub.add_parser("init", help="Initialize a new code review session")
    cmd.add_argument("--review-id", help="Custom review identifier")
    cmd.add_argument("--force", help="Overwrite existing state file", action="store_true")
    cmd.set_defaults(impl=impl)
