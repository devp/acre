import argparse

from cli.context import Context
from lib.commands_v0 import CommandsV0


def impl(args: argparse.Namespace, context: Context):
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )
    if not args.items:
        print("Need files to review")
        return
    cmdv0.cmd_review(args.items)


def register(sub: argparse._SubParsersAction):
    review = sub.add_parser("review")
    review.add_argument("items", nargs="*")
    # Removing this option for now:
    # g = review.add_mutually_exclusive_group()
    # g.add_argument("--skim", action="store_true")
    # g.add_argument("--deep", action="store_true")
    review.set_defaults(impl=impl)
