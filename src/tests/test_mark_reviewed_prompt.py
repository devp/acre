from cli.util import mark_reviewed_prompt, open_in_editor


def test_open_in_editor_uses_editor_and_appends_path():
    calls: list[list[str]] = []

    def run(cmd, **_kwargs):
        calls.append(list(cmd))
        return 0

    assert open_in_editor("foo.py", env={"EDITOR": "vim -f"}, run=run) is True
    assert calls == [["vim", "-f", "foo.py"]]


def test_mark_reviewed_prompt_allows_edit_then_yes():
    inputs = iter(["e", "y"])
    calls: list[list[str]] = []

    def input_fn(_prompt: str) -> str:
        return next(inputs)

    def run(cmd, **_kwargs):
        calls.append(list(cmd))
        return 0

    assert (
        mark_reviewed_prompt(
            path="bar.py",
            input_fn=input_fn,
            env={"EDITOR": "code -w"},
            run=run,
        )
        is True
    )
    assert calls == [["code", "-w", "bar.py"]]


def test_mark_reviewed_prompt_edit_without_editor_prints_and_reprompts():
    inputs = iter(["e", "n"])
    prints: list[str] = []

    def input_fn(_prompt: str) -> str:
        return next(inputs)

    def print_fn(msg: str):
        prints.append(msg)

    assert (
        mark_reviewed_prompt(
            path="baz.py",
            input_fn=input_fn,
            env={},
            print_fn=print_fn,
        )
        is False
    )
    assert any("EDITOR is not set" in msg for msg in prints)

