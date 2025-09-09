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


def register(sub: argparse._SubParsersAction):
    overview = sub.add_parser("overview")
    overview.set_defaults(impl=impl_overview)
    status = sub.add_parser("status")
    status.set_defaults(impl=impl_status)
    reset = sub.add_parser("reset")
    reset.set_defaults(impl=impl_reset)
