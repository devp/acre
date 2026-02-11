import argparse

from cli.context import Context
from cli.util import yn
from lib.commands_v0 import CommandsV0


def _select_paths_to_review(
    *,
    known_files: list[str],
    state,
    items: list[str] | None,
    todo: bool,
    loc_lte: int | None,
) -> list[str]:
    if items:
        resolved: list[str] = []
        for item in items:
            if item.isdigit():
                idx = int(item) - 1
                if 0 <= idx < len(known_files):
                    resolved.append(known_files[idx])
                continue
            if item in known_files:
                resolved.append(item)
        paths_to_review = resolved
    else:
        paths_to_review = list(known_files)

    if todo:
        paths_to_review = [p for p in paths_to_review if p and not state.is_file_reviewed(p)]

    if loc_lte is not None:
        paths_to_review = [
            p
            for p in paths_to_review
            if p and state.lines_of_file(p) is not None and state.lines_of_file(p) <= loc_lte
        ]

    return paths_to_review


def impl(args: argparse.Namespace, context: Context):
    state = context.state_manager.load_state(context.key)
    if not state:
        print("No state file found. Run 'init' first.")
        return
    known_files = list(state.files.keys())
    paths_to_review = _select_paths_to_review(
        known_files=known_files,
        state=state,
        items=list(args.items) if getattr(args, "items", None) else None,
        todo=bool(getattr(args, "todo", False)),
        loc_lte=getattr(args, "loc_lte", None),
    )
    
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )

    skim_mode = bool(hasattr(args, 'skim') and args.skim)
    test_diff_first = bool(hasattr(args, "test_diff_first") and args.test_diff_first)
    for path in paths_to_review:
        cmdv0.cmd_review(
            path=path,
            ask_approve=(False if skim_mode else True),
            test_diff_first=test_diff_first,
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
    review.add_argument(
        "--test-diff-first",
        dest="test_diff_first",
        action="store_true",
        help="For test files (per config review.test_file_patterns), show a filtered diff subset (review.test_diff_patterns) before the full diff",
    )
    review.set_defaults(impl=impl)
