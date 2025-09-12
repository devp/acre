import argparse

from cli.context import Context
from lib.commands_v0 import CommandsV0


def impl_overview(context: Context, **_):
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )
    cmdv0.cmd_overview()

def impl_status(context: Context, **_):
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )
    cmdv0.cmd_status()

def impl_reset(context: Context, args=None, **_):
    if args and getattr(args, 'destroy', False):
        from cli.util import yn
        if yn(f"Are you sure you want to permanently delete the review '{context.key}'?", default=False):
            context.state_manager.delete_state(context.key)
            print(f"Review '{context.key}' has been deleted.")
        else:
            print("Reset cancelled.")
        return
    
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )
    cmdv0.cmd_reset()

def impl_ls(context: Context, args, **_):
    todo_only = True if args.todo else False
    raw = getattr(args, 'raw', False)
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )
    cmdv0.cmd_list_files(todo_only=todo_only, raw=raw)


def register(sub: argparse._SubParsersAction):
    status = sub.add_parser("status", help="Status of review")
    status.set_defaults(impl=impl_status)
    ls = sub.add_parser("ls", help="List of files for this review, including their numbered indexes")
    ls.add_argument("--todo", action="store_true", help="Only list unreviewed files (without changing their indices)")
    ls.add_argument("--raw", action="store_true", help="Output only raw filenames separated by linebreaks")
    ls.set_defaults(impl=impl_ls)
    overview = sub.add_parser("overview")
    overview.set_defaults(impl=impl_overview, help="Print an overview of the request context, including status and list of files")
    reset = sub.add_parser("reset", help="Reset the progress of the code review")
    reset.add_argument("--destroy", action="store_true",
                      help="Permanently delete the review file (requires confirmation)")
    reset.set_defaults(impl=impl_reset)
