def progress_bar(pct: int, width: int = 20, color: bool = True) -> str:
    """Render an ASCII progress bar like [██████░░░░]."""
    pct = max(0, min(100, pct))
    filled = round(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    if color:
        green, reset = "\033[92m", "\033[0m"
        bar = f"{green}{'█' * filled}{reset}{'░' * (width - filled)}"
    return f"[{bar}]"


def print_whimsically(text: str):
    # Rainbow colors using ANSI escape codes
    colors = ['\033[91m', '\033[93m', '\033[92m', '\033[94m', '\033[95m', '\033[96m']  # Red, Yellow, Green, Blue, Magenta, Cyan
    reset = '\033[0m'

    # Color all pieces of the text
    text_parts = [
        f"{color}{char}{reset}"
        for i, char in enumerate(text)
        if (color := colors[i % len(colors)])
    ]
    print(''.join(text_parts))
