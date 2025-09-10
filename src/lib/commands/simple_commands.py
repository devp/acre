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

def impl_reset(context: Context, **_):
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )
    cmdv0.cmd_reset()

def impl_ls(context: Context, args, **_):
    todo_only = True if args.todo else False
    cmdv0 = CommandsV0(
        key=context.key,
        state_manager=context.state_manager,
        config=context.config,
    )
    cmdv0.cmd_list_files(todo_only=todo_only)

def register(sub: argparse._SubParsersAction):
    status = sub.add_parser("status", help="Status of review")
    status.set_defaults(impl=impl_status)
    ls = sub.add_parser("ls", help="List of files for this review, including their numbered indexes")
    ls.add_argument("--todo", action="store_true", help="Only list unreviewed files (without changing their indices)")
    ls.set_defaults(impl=impl_ls)
    overview = sub.add_parser("overview")
    overview.set_defaults(impl=impl_overview, help="Print an overview of the request context, including status and list of files")
    reset = sub.add_parser("reset", help="Reset the progress of the code review")
    reset.set_defaults(impl=impl_reset)
