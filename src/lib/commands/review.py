import argparse

from cli.context import Context
from lib.commands_v0 import CommandsV0


def impl(args: argparse.Namespace, context: Context):
    state = context.state_manager.load_state(context.key)
    known_files = list(state.files.keys()) if state else []
    if args.items:
        paths_to_review = [
            (known_files[int(item) - 1] if item.isdigit() else None)
            for item
            in args.items
        ]
    else:
        paths_to_review = known_files
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )
    for path in paths_to_review:
        cmdv0.cmd_review(path=path)


def register(sub: argparse._SubParsersAction):
    review = sub.add_parser("review")
    review.add_argument("items", nargs="*")
    # Removing this option for now:
    # g = review.add_mutually_exclusive_group()
    # g.add_argument("--skim", action="store_true")
    # g.add_argument("--deep", action="store_true")
    review.set_defaults(impl=impl)
