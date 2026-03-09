import os
import shlex
import subprocess
import webbrowser
from collections.abc import Callable, Mapping


def yn(prompt, default=False) -> bool:
    """Asks y/n with default on empty. Loops if unexpected input."""
    ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    if not ans:
        return default
    elif ans == "y":
        return True
    elif ans == "n":
        return False
    else:
        return yn(prompt, default)


def open_in_editor(
    path: str,
    *,
    env: Mapping[str, str] | None = None,
    run: Callable[..., object] = subprocess.run,
    print_fn: Callable[..., object] = print,
) -> bool:
    effective_env = os.environ if env is None else env
    editor = effective_env.get("EDITOR", "").strip()
    if not editor:
        return False

    try:
        cmd = shlex.split(editor)
    except ValueError as e:
        print_fn(f"Invalid $EDITOR: {e}")
        return False

    if not cmd:
        return False

    try:
        run([*cmd, path])
    except FileNotFoundError:
        print_fn(f"Editor command not found: {cmd[0]}")
        return False

    return True


def open_url(
    url: str,
    *,
    run: Callable[..., object] = subprocess.run,
    browser_open: Callable[[str], bool] = webbrowser.open,
    print_fn: Callable[..., object] = print,
) -> bool:
    try:
        run(["open", url])
        return True
    except FileNotFoundError:
        if browser_open(url):
            return True
        print_fn("Could not open URL in browser.")
        return False


def mark_reviewed_prompt(
    *,
    path: str,
    prompt: str = "Mark reviewed?",
    default: bool = False,
    on_peek: Callable[[], bool] | None = None,
    input_fn: Callable[[str], str] = input,
    env: Mapping[str, str] | None = None,
    run: Callable[..., object] = subprocess.run,
    print_fn: Callable[..., object] = print,
) -> bool:
    """
    Prompt for marking a file reviewed, with an edit-in-$EDITOR option.

    Accepted inputs:
    - y / yes
    - n / no
    - e / edit (opens $EDITOR for the file, then re-prompts)
    - p / peek (opens the GitHub diff view for the file, then re-prompts)
    - empty input returns `default`
    """
    while True:
        ans = input_fn(f"{prompt} [{'Y/n/e/p' if default else 'y/N/e/p'}] ").strip().lower()
        if not ans:
            return default
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        if ans in {"e", "edit"}:
            effective_env = os.environ if env is None else env
            editor = effective_env.get("EDITOR", "").strip()
            if not editor:
                print_fn("EDITOR is not set; set $EDITOR to use edit.")
                continue
            open_in_editor(path, env=env, run=run, print_fn=print_fn)
            continue
        if ans in {"p", "peek"}:
            if on_peek is None:
                print_fn("Peek is not available for this file.")
                continue
            on_peek()
            continue
