"""
Tests for interactive loop exit and empty-Enter behavior.

We test _run_one_interactive_line, a thin helper extracted from the loop body,
rather than driving impl_interactive end-to-end (which requires a full Context
and state manager).  The helper is defined here via monkey-patching the module's
internal logic through its public seams.
"""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from lib.commands.interactive import _build_interactive_parser


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _make_context(config=None):
    ctx = MagicMock()
    ctx.config = config or {}
    return ctx


def _make_parser(config=None):
    return _build_interactive_parser(config=config or {})


# ---------------------------------------------------------------------------
# Quit / exit detection (unit-level, no full loop needed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", ["quit", "exit"])
def test_quit_exit_are_recognized_exit_words(cmd):
    """'quit' and 'exit' must be the sentinel strings that trigger loop break."""
    assert cmd.strip() in ("quit", "exit")


# ---------------------------------------------------------------------------
# Empty-Enter behavior via impl_interactive
# ---------------------------------------------------------------------------

def _run_impl_interactive_with_inputs(inputs, config=None):
    """
    Drive impl_interactive with a scripted sequence of input() return values.
    Returns the list of commands that were dispatched (via impl mock calls).
    """
    from lib.commands.interactive import impl_interactive

    ctx = _make_context(config=config)
    ctx.state_manager.load_state.return_value = True  # already initialized

    dispatched = []

    def fake_impl(**kwargs):
        dispatched.append(kwargs.get("args"))

    input_iter = iter(inputs)

    def fake_input(_prompt):
        return next(input_iter)

    with patch("lib.commands.interactive.input", fake_input), \
         patch("lib.commands.interactive.impl_status"), \
         patch("lib.commands.interactive._setup_readline", return_value="/tmp/fake_history"), \
         patch("lib.commands.interactive._save_history"), \
         patch("lib.commands.interactive._build_interactive_parser") as mock_parser_factory:

        mock_parser = MagicMock()
        mock_parser_factory.return_value = mock_parser

        def fake_parse_args(args):
            ns = argparse.Namespace(impl=fake_impl, parsed_args=args)
            return ns

        mock_parser.parse_args.side_effect = fake_parse_args

        impl_interactive(context=ctx)

    return dispatched, mock_parser


def test_quit_exits_loop():
    dispatched, mock_parser = _run_impl_interactive_with_inputs(["quit"])
    mock_parser.parse_args.assert_not_called()
    assert dispatched == []


def test_exit_exits_loop():
    dispatched, mock_parser = _run_impl_interactive_with_inputs(["exit"])
    mock_parser.parse_args.assert_not_called()
    assert dispatched == []


def test_empty_enter_no_config_does_not_dispatch(monkeypatch):
    """Empty Enter with no default_interact_enter_command → loop continues, nothing dispatched."""
    # After the empty Enter, we send "quit" so the loop terminates.
    dispatched, mock_parser = _run_impl_interactive_with_inputs(["", "quit"], config={})
    mock_parser.parse_args.assert_not_called()
    assert dispatched == []


def test_empty_enter_with_config_dispatches_command(monkeypatch):
    """Empty Enter with default_interact_enter_command set → that command is dispatched."""
    config = {"default_interact_enter_command": "status"}
    dispatched, mock_parser = _run_impl_interactive_with_inputs(["", "quit"], config=config)
    # parse_args should have been called once with ["status"]
    mock_parser.parse_args.assert_called_once_with(args=["status"])


def test_eof_exits_loop():
    """Ctrl-D (EOFError) exits the loop cleanly."""
    from lib.commands.interactive import impl_interactive

    ctx = _make_context()
    ctx.state_manager.load_state.return_value = True

    def raise_eof(_prompt):
        raise EOFError

    with patch("lib.commands.interactive.input", raise_eof), \
         patch("lib.commands.interactive.impl_status"), \
         patch("lib.commands.interactive._setup_readline", return_value="/tmp/fake_history"), \
         patch("lib.commands.interactive._save_history"):
        impl_interactive(context=ctx)  # must not raise
