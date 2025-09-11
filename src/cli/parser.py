import argparse
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field

from cli.context import Context
from lib.commands.init import register as register_init
from lib.commands.review import register as register_review
from lib.commands.simple_commands import register as register_simple
from lib.commands.interactive import register as register_interactive
from lib.config.config import get_default_commands


class Commands(Enum):
    INIT = "init"
    OVERVIEW = "overview",
    STATUS = "status"
    RESET = "reset"
    REVIEW = "review"
    INTERACTIVE = "interactive"

class CommandOptions(Enum):
    REVIEW_SKIM = "review-skim"
    REVIEW_DEEP = "review-deep"
    INIT_FORCE = "init-force"

@dataclass
class CommandInstruction:
    command: Commands
    options: List[CommandOptions] = field(default_factory=list)
    filePath: str | None = None
    reviewId: str | None = None


def _build_argparse():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    register_init(sub)
    register_simple(sub)
    register_review(sub)
    register_interactive(sub)
    return p

_ArgParser = _build_argparse()

def print_usage():
    _ArgParser.print_usage()

def parse_args_from_cli(context: Context, override_args=None) -> Optional[CommandInstruction]:
    args: argparse.Namespace = _ArgParser.parse_args(args=override_args)
    if args.cmd is None:
        default_commands = get_default_commands(context.config)
        if default_commands:
            parse_args_from_cli(context=context, override_args=default_commands)
        else:
            print_usage()
    else:
        if "impl" in args:
            args.impl(args=args, context=context)
        else:
            print("Not implemented:", args.cmd)
            exit(1)
