import argparse

from cli.context import Context
from lib.hunk_filter import _strip_ansi
from lib.sources.git import diff_lines


def _resolve_path(state, item: str) -> str | None:
    files = list(state.files.keys())
    if item.isdigit():
        idx = int(item) - 1
        if 0 <= idx < len(files):
            return files[idx]
        return None
    return item if item in state.files else None


def _parse_hunk_number(hunk_arg: str) -> int | None:
    s = hunk_arg.strip().lstrip("Hh")
    try:
        return int(s)
    except ValueError:
        return None


def _find_hunk_range(lines: list[str], hunk_num: int) -> tuple[int | None, int | None]:
    hunk_idx = 0
    hunk_start: int | None = None
    for i, line in enumerate(lines, start=1):
        if _strip_ansi(line).startswith("@@"):
            hunk_idx += 1
            if hunk_idx == hunk_num:
                hunk_start = i
            elif hunk_start is not None:
                return hunk_start, i - 1
    if hunk_start is not None:
        return hunk_start, len(lines)
    return None, None


def impl(args: argparse.Namespace, context: Context):
    state = context.state_manager.load_state(context.key)
    if not state:
        print("No state file found. Run 'init' first.")
        return

    path = _resolve_path(state, args.file)
    if path is None:
        print(f"Could not resolve file: {args.file}")
        return

    if args.clear:
        context.state_manager.clear_preapproved_blocks(state, path=path)
        context.state_manager.save_state(state)
        print(f"Cleared preapproved blocks for {path}")
        return

    if args.hunk is not None:
        hunk_num = _parse_hunk_number(args.hunk)
        if hunk_num is None:
            print(f"Invalid hunk selector: {args.hunk}")
            return
        lines = diff_lines(path, diff_target=state.diff_target())
        start_line, end_line = _find_hunk_range(lines, hunk_num)
        if start_line is None or end_line is None:
            print(f"Hunk {hunk_num} not found in diff for {path}")
            return
        context.state_manager.add_preapproved_block(
            state, path=path, start_line=start_line, end_line=end_line
        )
        context.state_manager.save_state(state)
        print(f"Preapproved hunk {hunk_num} (lines {start_line}-{end_line}) of {path}")
        return

    if args.start_line is None or args.end_line is None:
        print("Provide start_line and end_line, or --hunk N, or --clear")
        return

    notes: str = args.notes or ""
    context.state_manager.add_preapproved_block(
        state, path=path, start_line=args.start_line, end_line=args.end_line, notes=notes
    )
    context.state_manager.save_state(state)
    print(f"Preapproved lines {args.start_line}-{args.end_line} of {path}")


def register(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "preapprove",
        help="Mark diff line ranges as pre-approved, hiding them from future review diffs",
    )
    p.add_argument("file", help="File path or 1-based index from ls")
    p.add_argument("start_line", nargs="?", type=int, help="Start diff line number (1-based)")
    p.add_argument("end_line", nargs="?", type=int, help="End diff line number (1-based, inclusive)")
    p.add_argument("--notes", default="", help="Optional notes about why this range is pre-approved")
    p.add_argument("--clear", action="store_true", help="Clear all preapproved blocks for this file")
    p.add_argument(
        "--hunk",
        metavar="N",
        help="Pre-approve a whole hunk by number (e.g. 1 or H01)",
    )
    p.set_defaults(impl=impl)
