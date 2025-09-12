import argparse

from cli.context import Context
from lib.commands_v0 import CommandsV0


def impl(args: argparse.Namespace, context: Context):
    state = context.state_manager.load_state(context.key)
    if not state:
        print("No state file found. Run 'init' first.")
        return
    known_files = list(state.files.keys())
    if args.items:
        paths_to_review = [
            (known_files[int(item) - 1] if item.isdigit() else None)
            for item
            in args.items
        ]
    else:
        paths_to_review = known_files
    
    if args.todo:
        paths_to_review = [
            path for path in paths_to_review 
            if path and not state.is_file_reviewed(path)
        ]
    
    if hasattr(args, 'loc_lte') and args.loc_lte is not None:
        paths_to_review = [
            path for path in paths_to_review
            if path and state.lines_of_file(path) is not None and state.lines_of_file(path) <= args.loc_lte
        ]
    
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
    review.add_argument("--todo", action="store_true", help="Only review unreviewed files")
    review.add_argument("--loc-lte", type=int, help="Only review files with lines changed <= this number")
    review.set_defaults(impl=impl)
