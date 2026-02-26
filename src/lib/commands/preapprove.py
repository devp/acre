import argparse

from cli.context import Context


def impl(args: argparse.Namespace, context: Context):
    state = context.state_manager.load_state(context.key)
    if not state:
        print("No state file found. Run 'init' first.")
        return

    known_files = list(state.files.keys())
    path = args.path_or_index
    if path.isdigit():
        idx = int(path)
        if idx < 1 or idx > len(known_files):
            raise Exception(f"Invalid file index: {idx}")
        path = known_files[idx - 1]

    context.state_manager.add_preapproved_block(
        state,
        path=path,
        start_line=args.start_line,
        end_line=args.end_line,
        notes=args.notes or "",
    )
    context.state_manager.save_state(state)
    print(f"> Preapproved {path}:{args.start_line}-{args.end_line}")


def register(sub: argparse._SubParsersAction):
    cmd = sub.add_parser(
        "preapprove",
        help="Hide a range of rendered diff output lines for a file during review",
    )
    cmd.add_argument(
        "path_or_index",
        help="Path to file, or numeric index from `ls` output (must exist in current review state)",
    )
    cmd.add_argument("start_line", type=int, help="Start diff-output line (1-based)")
    cmd.add_argument("end_line", type=int, help="End diff-output line (1-based, inclusive)")
    cmd.add_argument("--notes", help="Optional note for this preapproval", default="")
    cmd.set_defaults(impl=impl)
