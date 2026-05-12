from lib.config.config import get_default_interact_enter_command


def test_returns_none_when_unset():
    assert get_default_interact_enter_command({}) is None


def test_returns_none_when_empty_string():
    assert get_default_interact_enter_command({"default_interact_enter_command": ""}) is None


def test_parses_string():
    config = {"default_interact_enter_command": "ls --todo"}
    assert get_default_interact_enter_command(config) == ["ls", "--todo"]


def test_parses_list():
    config = {"default_interact_enter_command": ["ls", "--todo"]}
    assert get_default_interact_enter_command(config) == ["ls", "--todo"]


def test_returns_none_for_empty_list():
    assert get_default_interact_enter_command({"default_interact_enter_command": []}) is None
