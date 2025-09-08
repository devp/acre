import argparse
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field


class Commands(Enum):
    INIT = "init"
    OVERVIEW = "overview",
    STATUS = "status"
    RESET = "reset"
    REVIEW = "review"

class CommandOptions(Enum):
    REVIEW_SKIM = "review-skim"
    REVIEW_DEEP = "review-deep"
    INTERACTIVE = "interactive"
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
    init = sub.add_parser("init", help="Initialize a new code review session")
    init.add_argument("--review-id", help="Custom review identifier")
    init.add_argument("--force", help="Overwrite existing state file", action="store_true")
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
        case "init":
            return CommandInstruction(
                command=Commands.INIT,
                reviewId=getattr(args, 'review_id', None),
                options=[CommandOptions.INIT_FORCE] if args.force else []
            )
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
