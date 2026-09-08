import argparse

from cli.context import Context
from lib.config.config import get_diff_git_args
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


def _parse_range_arg(range_arg: str) -> tuple[str, int | None, int | None, int | None]:
    """
    Parses the unified range positional into (mode, hunk_num, start_line, end_line).

    Supported forms:
      N      → hunk N (plain integer or H/h-prefixed, e.g. H02)
      N:M    → line range N to M
      :M     → line range 1 to M
      N:     → line range N to end of diff
    Returns ('invalid', None, None, None) on parse error.
    """
    if ":" in range_arg:
        start_str, _, end_str = range_arg.partition(":")
        try:
            start = int(start_str) if start_str else None
            end = int(end_str) if end_str else None
        except ValueError:
            return ("invalid", None, None, None)
        return ("lines", None, start, end)
    stripped = range_arg.strip().lstrip("Hh")
    try:
        return ("hunk", int(stripped), None, None)
    except ValueError:
        return ("invalid", None, None, None)


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

    if args.range is None:
        print("Provide hunk number, line range (N:M, :M, or N:), or --clear")
        return

    mode, hunk_num, start_line, end_line = _parse_range_arg(args.range)
    if mode == "invalid":
        print(f"Invalid range: {args.range!r}")
        return

    if mode == "hunk":
        assert hunk_num is not None
        lines = diff_lines(path, diff_target=state.diff_target(), git_args=get_diff_git_args(context.config))
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

    # mode == "lines"
    if start_line is None:
        start_line = 1
    if end_line is None:
        lines = diff_lines(path, diff_target=state.diff_target(), git_args=get_diff_git_args(context.config))
        end_line = len(lines)
    notes: str = args.notes or ""
    context.state_manager.add_preapproved_block(
        state, path=path, start_line=start_line, end_line=end_line, notes=notes
    )
    context.state_manager.save_state(state)
    print(f"Preapproved lines {start_line}-{end_line} of {path}")


def register(sub: argparse._SubParsersAction):
    p = sub.add_parser(
        "preapprove",
        help="Mark diff hunks or line ranges as pre-approved, hiding them from future review diffs",
    )
    p.add_argument("file", help="File path or 1-based index from ls")
    p.add_argument(
        "range",
        nargs="?",
        help="Hunk number (e.g. 2 or H02), or line range (N:M, :M, or N:)",
    )
    p.add_argument("--notes", default="", help="Optional notes about why this range is pre-approved")
    p.add_argument("--clear", action="store_true", help="Clear all preapproved blocks for this file")
    p.set_defaults(impl=impl)
