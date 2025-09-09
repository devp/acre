import argparse
import shlex

from cli.context import Context


def _build_interactive_parser():
    parser = argparse.ArgumentParser(prog="", description="Interactive session")
    subparsers = parser.add_subparsers(dest="cmd")

    def impl_hello(name, **_):
        print(f"Hello, {name}!")

    hello_parser = subparsers.add_parser("hello", help="Prints a greeting")
    hello_parser.add_argument("name", help="The name to greet")
    hello_parser.set_defaults(impl=impl_hello)

    exit_parser = subparsers.add_parser("exit", help="Exits the interactive session")
    exit_parser.set_defaults(impl=lambda **_: exit(0))

    return parser


def impl_interactive(context: Context, **_):
    print("Entering interactive mode. Type 'exit' or an empty line to quit.")
    parser = _build_interactive_parser()
    while True:
        try:
            line = input("> ")
            if not line.strip():
                break

            try:
                args = parser.parse_args(shlex.split(line))
                if "impl" in args:
                    args.impl(**vars(args))
                else:
                    parser.print_help()
            except SystemExit:
                # Argparse calls exit() on --help or errors, so we catch it
                pass
        except EOFError:
            break
    print("Exiting interactive mode.")


def register(sub: argparse._SubParsersAction):
    parser = sub.add_parser("interactive", help="Starts an interactive session")
    parser.set_defaults(impl=impl_interactive)
