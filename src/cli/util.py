def yn(prompt, default=False):
    ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    if not ans:
        return default
    return ans == "y"


def are_all_integers(items):
    return all(item.isdigit() for item in items)
