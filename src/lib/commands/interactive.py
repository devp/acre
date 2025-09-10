import argparse
import shlex

from cli.context import Context
from cli.util import yn
from lib.commands.review import register as register_review
from lib.commands.simple_commands import impl_status, register as register_simple
from lib.config.config import resolve_cmd_from_config_aliases
from lib.initialize import cmd_init


def _build_interactive_parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    # Including existing commands
    register_simple(sub)
    register_review(sub)

    # Interactive-only command (help)
    def impl_help(**_):
        p.print_usage()
    help = sub.add_parser("help", aliases=["h", "?"])
    help.set_defaults(impl=impl_help)

    return p


def impl_interactive(context: Context, **_):
    print("Entering interactive mode.")
    
    # Check if PR is initialized
    if not context.state_manager.load_state(context.key):
        print(f"No initialized review found for '{context.key}'")
        if yn("Initialize now?", default=False):
            cmd_init(state_manager=context.state_manager, review_id=context.key)
        else:
            print("Cannot proceed without initialized review. Exiting.")
            return
    
    parser = _build_interactive_parser()
    while True:
        try:
            impl_status(context=context)
            line = input("> ")
            if not line.strip():
                break
            try:
                raw_args = shlex.split(line)
                expanded_args = resolve_cmd_from_config_aliases(cmd=raw_args[0], config=context.config) + raw_args[1:]
                args = parser.parse_args(args=expanded_args)
                if "impl" in args:
                    args.impl(args=args, context=context)
                else:
                    print("Command not implemented.", args)
            except SystemExit:
                # Argparse calls exit() on --help or errors, so we catch it
                pass
        except EOFError:
            break
    print("Exiting interactive mode.")


def register(sub: argparse._SubParsersAction):
    parser = sub.add_parser("interactive", help="Starts an interactive session")
    parser.set_defaults(impl=impl_interactive)
