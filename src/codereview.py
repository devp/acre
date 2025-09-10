#!/usr/bin/env python3
import sys

from cli.context import Context as CLI_Context
from cli.parser import _ArgParser
from lib.config.config import load_config, resolve_cmd_from_config_aliases
from lib.review_identifier import ReviewIdentifier
from lib.sources.git import get_current_commit_sha, get_repo_root
from lib.state import StateManager
from lib.commit_range import CommitRangeNormalizer


def _rewrite_args_via_aliases(config):
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        expanded = resolve_cmd_from_config_aliases(cmd=cmd, config=config)
        sys.argv = [sys.argv[0]] + expanded + sys.argv[2:]


def main():
    config = load_config()
    _rewrite_args_via_aliases(config)
    
    # Parse args to get global commit range options
    args = _ArgParser.parse_args()
    
    # Determine commit range and review key
    commit_range = CommitRangeNormalizer.normalize(
        commit=getattr(args, 'commit', None),
        from_ref=getattr(args, 'from_ref', None),
        to_ref=getattr(args, 'to_ref', None)
    )
    key = ReviewIdentifier.determine_review_id(commit_range=commit_range)
    
    state_manager = StateManager(
            repo_root=get_repo_root(),
            current_sha=get_current_commit_sha(),
    )
    context = CLI_Context(key=key, state_manager=state_manager, config=config)
    
    # Call the command implementation
    if args.cmd is None:
        _ArgParser.print_usage()
    else:
        if "impl" in args:
            args.impl(args=args, context=context)
        else:
            print("Not implemented:", args.cmd)
            sys.exit(1)

if __name__ == "__main__":
    main()
