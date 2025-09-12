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
