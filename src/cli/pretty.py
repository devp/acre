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
