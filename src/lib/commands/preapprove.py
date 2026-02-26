import argparse
import re

from cli.context import Context
from lib.sources.git import diff_lines


_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _strip_ansi(s: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", s)


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

    if args.clear:
        context.state_manager.clear_preapproved_blocks(state, path=path)
        context.state_manager.save_state(state)
        print(f"> Cleared preapprovals for {path}")
        return

    start_line = args.start_line
    end_line = args.end_line
    if args.hunk is not None:
        diff_target = state.diff_target()
        lines = diff_lines(path, diff_target=diff_target)
        hunk_index = _parse_hunk_selector(args.hunk)
        start_line, end_line = _get_hunk_line_range(lines, hunk_index=hunk_index)
        notes = args.notes or ""
    else:
        if start_line is None or end_line is None:
            raise Exception("Must provide START_LINE and END_LINE (or use --hunk)")
        notes = args.notes or ""

    context.state_manager.add_preapproved_block(
        state,
        path=path,
        start_line=start_line,
        end_line=end_line,
        notes=notes,
    )
    context.state_manager.save_state(state)
    print(f"> Preapproved {path}:{start_line}-{end_line}")


def _get_hunk_line_range(diff_lines_for_file: list[str], *, hunk_index: int) -> tuple[int, int]:
    if hunk_index < 1:
        raise Exception(f"Invalid hunk index: {hunk_index}")

    current = 0
    hunk_start: int | None = None
    hunk_end: int | None = None

    for idx, line in enumerate(diff_lines_for_file, start=1):
        if _strip_ansi(line).startswith("@@"):
            current += 1
            if current == hunk_index:
                hunk_start = idx
                hunk_end = idx
            elif current == hunk_index + 1 and hunk_start is not None:
                # End at the line before the next hunk header.
                return (hunk_start, (idx - 1))

        if hunk_start is not None and current == hunk_index:
            hunk_end = idx

    if hunk_start is None or hunk_end is None:
        raise Exception(f"Hunk not found: {hunk_index}")
    return (hunk_start, hunk_end)


def _parse_hunk_selector(raw: str) -> int:
    # Accept either plain integers ("1") or the review display form ("H01").
    s = raw.strip()
    if s.lower().startswith("h"):
        s = s[1:]
    try:
        idx = int(s)
    except ValueError as e:
        raise Exception(f"Invalid hunk selector: {raw}") from e
    if idx < 1:
        raise Exception(f"Invalid hunk index: {idx}")
    return idx


def register(sub: argparse._SubParsersAction):
    cmd = sub.add_parser(
        "preapprove",
        help="Hide a range of rendered diff output lines for a file during review",
    )
    cmd.add_argument(
        "path_or_index",
        help="Path to file, or numeric index from `ls` output (must exist in current review state)",
    )
    cmd.add_argument("start_line", type=int, nargs="?", help="Start diff-output line (1-based)")
    cmd.add_argument("end_line", type=int, nargs="?", help="End diff-output line (1-based, inclusive)")
    cmd.add_argument(
        "--hunk",
        help="Preapprove an entire hunk by index (e.g. 1) or by displayed label (e.g. H01)",
    )
    cmd.add_argument(
        "--clear",
        action="store_true",
        help="Clear all preapproved blocks for the specified file",
    )
    cmd.add_argument("--notes", help="Optional note for this preapproval", default="")
    cmd.set_defaults(impl=impl)
