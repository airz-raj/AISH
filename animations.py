# animations.py
"""
Animations for AISH CLI
Provides:
 - display_banner()      -> show centered AISH banner + "By AIRZ01"
 - glitch_animation(text, repeat=2, delay=0.05)
 - impact_animation()    -> dynamic non-verbal "blast" / error effect
Works with colorama and optionally pyfiglet (falls back if not available).
"""

import sys
import time
import shutil
import random

from colorama import init, Fore, Style

# try to use pyfiglet for nicer banner; fallback to simple ASCII
try:
    from pyfiglet import Figlet
    _HAVE_PYFIGLET = True
except Exception:
    _HAVE_PYFIGLET = False

# initialize colorama
init(autoreset=True)

# Professional non-rainbow gradient palette (cool tones)
_COLORS = [Fore.CYAN, Fore.LIGHTBLUE_EX, Fore.MAGENTA]

# Utility: terminal width / center
def _term_width():
    try:
        return shutil.get_terminal_size((80, 20)).columns
    except Exception:
        return 80

def _center(text):
    width = _term_width()
    # center each line individually
    return "\n".join(line.center(width) for line in text.splitlines())

def _gradient_text(text):
    """
    Apply a simple smooth-ish gradient (from _COLORS) across the characters of text.
    We distribute colors evenly over the text length so it's a subtle multi-color effect.
    """
    if not text:
        return ""
    n = len(text)
    k = len(_COLORS)
    colored = []
    for i, ch in enumerate(text):
        # pick color based on position relative to text length (smooth mapping)
        idx = int((i / max(1, n - 1)) * (k - 1))
        color = _COLORS[idx % k]
        colored.append(f"{color}{ch}")
    return "".join(colored) + Style.RESET_ALL

def glitch_animation(text, repeat=2, delay=0.05):
    """
    Show a glitch effect then settle to the final text.
    Parameters:
      text (str): text to display (single-line)
      repeat (int): how many glitch frames before settling
      delay (float): time between frames
    """
    if not isinstance(text, str):
        text = str(text)

    # characters used for glitching
    glitch_chars = list("@#%&*?+=-:;.,<>/\\|[]{}()")
    for _ in range(repeat):
        # create a glitched string of same length
        glitched = "".join(
            random.choice(glitch_chars) if random.random() < 0.45 else ch
            for ch in text
        )
        out = _center(_gradient_text(glitched))
        # overwrite by printing (we print each frame as its own line for stability)
        sys.stdout.write("\r" + out)
        sys.stdout.flush()
        time.sleep(delay)
        # move to next line briefly to avoid weird terminal behaviors
        sys.stdout.write("\r")
    # final settled line
    settled = _center(_gradient_text(text))
    print(settled)

def impact_animation(iterations: int = 6):
    """
    Dynamic non-verbal impact/error animation.
    Prints a few rows of moving symbols then a short central block to indicate impact.
    Does not print literal 'BOOM' text.
    """
    width = _term_width()
    symbols = ["*", "+", "x", "•", "o", "·"]
    # limit row width so output doesn't overflow small terminals
    max_block = max(10, width // 3)

    for i in range(iterations):
        # random offset left margin
        left_margin = " " * random.randint(0, max(0, width // 6))
        block_len = random.randint(max(8, max_block // 2), max_block)
        block = "".join(random.choice(symbols) for _ in range(block_len))
        line = left_margin + block
        # color variation: red-ish for impact feel
        color = Fore.LIGHTRED_EX if i % 2 == 0 else Fore.RED
        print(color + line)
        time.sleep(0.04)

    # central solid block as the "impact"
    block_width = max(12, width // 4)
    center_block = "█" * block_width
    print(Fore.RED + _center(center_block))
    time.sleep(0.09)

    # short fade: print a few dimmer lines below
    for j in range(2):
        fade_line = " " * random.randint(0, width // 5) + "".join(random.choice(symbols) for _ in range(block_width // 2))
        print(Fore.MAGENTA + fade_line)
        time.sleep(0.05)

def display_banner():
    """
    Display the AISH banner centered with a subtle gradient and the 'By AIRZ01' byline.
    Uses pyfiglet if present; otherwise uses a simple prebuilt ASCII banner.
    Includes a brief glitch intro for effect.
    """
    try:
        # small glitch intro of the short label
        try:
            glitch_animation("AISH", repeat=4, delay=0.06)
        except Exception:
            # if glitch fails, proceed silently
            pass

        if _HAVE_PYFIGLET:
            f = Figlet(font="slant")
            raw = f.renderText("AISH")
            # print banner lines with gradient and slight reveal delay
            for line in raw.splitlines():
                if not line.strip():
                    print()  # preserve spacing
                    continue
                colored = _gradient_text(line)
                print(_center(colored))
                time.sleep(0.02)
        else:
            # fallback ASCII banner (clean, fixed)
            banner = r"""
 █████╗ ██╗███████╗██╗  ██╗
██╔══██╗██║██╔════╝██║ ██╔╝
███████║██║███████╗█████╔╝ 
██╔══██║██║╚════██║██╔═██╗ 
██║  ██║██║███████║██║  ██╗
╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝
"""
            for line in banner.splitlines():
                if not line.strip():
                    print()
                    continue
                print(_center(_gradient_text(line)))
                time.sleep(0.02)

        # Byline centered underneath
        byline = "By AIRZ01"
        print()
        print(_center(Fore.CYAN + Style.BRIGHT + byline + Style.RESET_ALL))
        print()  # small gap
    except Exception:
        # ultimate fallback: minimal safe prints
        try:
            print("\n\n" + "AISH".center(_term_width()))
            print("By AIRZ01".center(_term_width()))
        except Exception:
            # if even that fails, do nothing (caller will fallback)
            pass
