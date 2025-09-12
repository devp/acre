import argparse

from cli.context import Context
from cli.util import yn, ynxyz
from lib.models import ReviewState
from lib.sources.git import diff
from lib.state import StateManager

def impl_review_one(
        path: str,
        state_manager: StateManager,
        state: ReviewState,
        ask_approve=True,
):
    """Reviews a single file"""
    if state.is_file_reviewed(path):
        print(f"{path} already reviewed")
        return False
    diff(path, diff_target=state.diff_target())
    if not ask_approve:
        return
    
    def _mark_reviewed():
        state_manager.mark_file_reviewed(state, path)
        state_manager.save_state(state)
        lines = state.lines_of_file(path)
        print(f"> Marked {lines} lines as reviewed")

    while True:
        response, other_cmd = ynxyz("Mark reviewed? ([c]opy filename, [e]dit file)")
        if response is True:
            _mark_reviewed()
            break
        elif response is False:
            break
        else:
            match (other_cmd and other_cmd.lower()):
                case "c":
                    print("Not implemented")
                    continue
                case "e":
                    print("Not implemented") 
                    continue

def impl(args: argparse.Namespace, context: Context):
    state = context.state_manager.load_state(context.key)
    if not state:
        print("No state file found. Run 'init' first.")
        return
    known_files = list(state.files.keys())
    if args.items:
        paths_to_review = [
                path
                for path in [
                    (known_files[int(item) - 1] if item.isdigit() else None)
                    for item in args.items
                ]
                if path is not None
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
    
    skim_mode = bool(hasattr(args, 'skim') and args.skim)
    for path in paths_to_review:
        impl_review_one(
            path=path,
            state=state,
            state_manager=context.state_manager,
            ask_approve=(False if skim_mode else True)
        )
    if skim_mode:
        if yn("Approve all files?"):
            for path in paths_to_review:
                context.state_manager.mark_file_reviewed(state=state, path=path)
            context.state_manager.save_state(state)
            print(f"> Marked {len(paths_to_review)} files as reviewed (skim mode)")


def register(sub: argparse._SubParsersAction):
    review = sub.add_parser("review", help="Review one or more files")
    review.add_argument("items", nargs="*", help="Items defined as either paths or indexes from `ls` command. "
        "If none provided, review all files.")
    review.add_argument("--todo", action="store_true", help="Only review unreviewed files")
    review.add_argument("--skim", action="store_true", help="Show all diffs and ask for approval as a whole")
    review.add_argument("--loc-lte", type=int, help="Only review files with lines changed <= this number")
    review.set_defaults(impl=impl)
