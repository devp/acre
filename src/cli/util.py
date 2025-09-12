from typing import Tuple, Union


type YNXYZ_RetVal = Union[Tuple[bool, None], Tuple[None, str]]

def ynxyz(prompt: str, default: bool = False, other_cmds: list[str] = []) -> YNXYZ_RetVal:
    """
    Asks y/n utility, also accepts other commands.
    Returns tuple (bool|None, str) where:
    - bool is set for y/n responses 
    - str is the raw input for other commands
    """
    ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    if not ans:
        return default, None
    elif ans == "y":
        return True, None
    elif ans == "n":
        return False, None
    elif ans in other_cmds:
        return None, ans
    else:
        return ynxyz(prompt, default, other_cmds)

def yn(prompt, default=False) -> bool:
    """Asks y/n with default on empty. Loops if unexpected input."""
    result, _ = ynxyz(prompt, default)
    if result is None:
        return yn(prompt, default)
    return result
