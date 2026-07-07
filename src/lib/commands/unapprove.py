import argparse

from cli.context import Context
from lib.commands.review import _select_paths_to_review


def impl(args: argparse.Namespace, context: Context):
    state = context.state_manager.load_state(context.key)
    if not state:
        print("No state file found. Run 'init' first.")
        return

    known_files = list(state.files.keys())
    paths = _select_paths_to_review(
        known_files=known_files,
        state=state,
        items=list(args.items),
        todo=False,
        loc_lte=None,
    )

    if not paths:
        print("No matching files found for:", ", ".join(args.items))
        exit(1)

    for path in paths:
        context.state_manager.unmark_file_reviewed(state, path)
    context.state_manager.save_state(state)
    print(f"> Unapproved {len(paths)} file(s): {', '.join(paths)}")


def register(sub: argparse._SubParsersAction):
    unapprove = sub.add_parser(
        "unapprove",
        help="Revert one or more files back to unreviewed",
    )
    unapprove.add_argument(
        "items",
        nargs="+",
        help="Files to unapprove, as paths or indexes from `ls`",
    )
    unapprove.set_defaults(impl=impl)
