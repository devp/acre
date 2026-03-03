from lib.commands.interactive import _expand_interactive_argv


def test_expand_interactive_argv_rewrites_ints_to_default_command():
    config = {"default_interact_command_for_args": "review"}
    assert _expand_interactive_argv(raw_args=["1", "2", "3"], config=config) == ["review", "1", "2", "3"]


def test_expand_interactive_argv_default_command_supports_alias_expansion():
    config = {
        "default_interact_command_for_args": "r --todo",
        "aliases": {"r": "review"},
    }
    assert _expand_interactive_argv(raw_args=["7"], config=config) == ["review", "--todo", "7"]


def test_expand_interactive_argv_non_ints_use_normal_alias_expansion():
    config = {"aliases": {"st": "status"}}
    assert _expand_interactive_argv(raw_args=["st"], config=config) == ["status"]
