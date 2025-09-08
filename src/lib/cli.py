import argparse
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field


class Commands(Enum):
    OVERVIEW = "overview",
    STATUS = "status"
    RESET = "reset"
    REVIEW = "review"

class CommandOptions(Enum):
    REVIEW_SKIM = "review-skim"
    REVIEW_DEEP = "review-deep"
    INTERACTIVE = "interactive"

@dataclass
class CommandInstruction:
    command: Commands
    options: List[CommandOptions] = field(default_factory=list)
    filePath: str | None = None


def _build_argparse():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    over = sub.add_parser("overview")
    over.add_argument("-i", "--interactive", action="store_true")
    sub.add_parser("status")
    sub.add_parser("reset")
    r = sub.add_parser("review")
    r.add_argument("file")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--skim", action="store_true")
    g.add_argument("--deep", action="store_true")
    return p

_ArgParser = _build_argparse()

def print_usage():
    _ArgParser.print_usage()

def parse_args_from_cli(override_args=None) -> Optional[CommandInstruction]:
    args: argparse.Namespace = _ArgParser.parse_args(args=override_args)
    match args.cmd:
        case "overview":
            return CommandInstruction(
                command=Commands.OVERVIEW,
                options=[CommandOptions.INTERACTIVE] if args.interactive else []
            )
        case "status":
            return CommandInstruction(command=Commands.STATUS)
        case "reset":
            return CommandInstruction(command=Commands.RESET)
        case "review":
            return CommandInstruction(
                command=Commands.REVIEW,
                options=[
                    (CommandOptions.REVIEW_DEEP
                     if args.deep
                     else CommandOptions.REVIEW_SKIM),
                ],
                filePath=args.file,
            )
    return None
