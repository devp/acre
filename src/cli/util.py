def yn(prompt, default=False):
    ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    if not ans:
        return default
    return ans == "y"
