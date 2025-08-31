# executor.py
import os
import subprocess
from typing import List, Optional
from colorama import Fore, Style
from utils import detect_os
import json

import time
import random
from typing import List, Optional
from colorama import Fore, Style
# Load patterns and command mappings
with open("patterns.json") as f:
    PATTERNS = json.load(f)

with open("commands.json") as f:
    COMMANDS_JSON = json.load(f)
# executor.py - Add these imports and functions at the top:


# Add animation functions directly to executor.py
def processing_animation(duration: float = 0.9):
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end = time.time() + duration
    while time.time() < end:
        for s in spinner:
            print("\r" + Fore.YELLOW + "Processing " + s + Style.RESET_ALL, end="", flush=True)
            time.sleep(0.06)
            if time.time() >= end:
                break
    print("\r" + " " * 40 + "\r", end="", flush=True)

def success_animation():
    symbols = ["*", "+", "·", "•"]
    cols = [Fore.GREEN, Fore.LIGHTGREEN_EX]
    for _ in range(4):
        row = "".join(random.choice(cols) + random.choice(symbols) for _ in range(24))
        print(row + Style.RESET_ALL)
        time.sleep(0.02)
    print(Fore.GREEN + "✔ Success!" + Style.RESET_ALL)

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def box_print(title: str, lines: List[str], color: str = "yellow"):
    color_map = {
        "yellow": Fore.YELLOW,
        "green": Fore.GREEN,
        "red": Fore.RED,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN
    }
    C = color_map.get(color, Fore.YELLOW)
    width = max(len(title) + 4, *(len(l) for l in lines), 40)
    header = C + f"┌─[{title}]" + "─" * (width - len(title) - 4) + "┐" + Style.RESET_ALL
    print(header)
    for line in lines:
        print(C + "│ " + Style.RESET_ALL + f"{line}")
    print(C + "└" + "─" * width + "┘" + Style.RESET_ALL)

# Now the existing execute_command function:
def execute_command(parsed, show_animations=True):
    """
    parsed is tuple from parser:
    ("builtin", func, args:list) or ("shell", command_string)
    show_animations: whether to show processing/success animations
    """
    if not parsed:
        return

    kind = parsed[0]
    if kind == "builtin":
        func = parsed[1]
        args = parsed[2] if len(parsed) > 2 else []
        try:
            if show_animations:
                processing_animation()
            func(args)
            if show_animations:
                success_animation()
        except SystemExit:
            raise
        except Exception as e:
            if show_animations:
                box_print("Error", [str(e)], color="red")
            else:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    elif kind == "shell":
        cmd = parsed[1]
        # detect if request to clear
        if cmd.strip().lower() in ("clear", "cls"):
            clear_screen()
            return
        try:
            proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            if out:
                if show_animations:
                    box_print(f"OUTPUT: {cmd}", out.splitlines(), color="green")
                else:
                    print(f"{Fore.GREEN}Output:{Style.RESET_ALL}")
                    print(out)
            if err:
                if show_animations:
                    box_print(f"ERROR: {cmd}", err.splitlines(), color="red")
                else:
                    print(f"{Fore.RED}Error:{Style.RESET_ALL}")
                    print(err)
            if not out and not err:
                if show_animations:
                    box_print("RESULT", ["(no output)"], color="yellow")
                else:
                    print(f"{Fore.YELLOW}(no output){Style.RESET_ALL}")
        except Exception as e:
            if show_animations:
                box_print("Execution error", [str(e)], color="red")
            else:
                print(f"{Fore.RED}Execution error: {e}{Style.RESET_ALL}")
# simple box printer, matching the minimal yellow/green style
def box_print(title: str, lines: List[str], color: str = "yellow"):
    color_map = {
        "yellow": Fore.YELLOW,
        "green": Fore.GREEN,
        "red": Fore.RED,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN
    }
    C = color_map.get(color, Fore.YELLOW)
    width = max(len(title) + 4, *(len(l) for l in lines), 40)
    header = C + f"┌─[{title}]" + "─" * (width - len(title) - 4) + "┐" + Style.RESET_ALL
    print(header)
    for line in lines:
        print(C + "│ " + Style.RESET_ALL + f"{line}")
    print(C + "└" + "─" * width + "┘" + Style.RESET_ALL)

def clear_screen():
    os.system("cls" if detect_os() == "windows" else "clear")

def resolve_command(user_input: str) -> str:
    """
    Map natural language input → command key → OS-specific command string
    """
    user_input = user_input.strip().lower()
    cmd_key = PATTERNS.get(user_input)  # Step 1: NL → command key
    if not cmd_key:
        return user_input  # fallback to passthrough

    # Step 2: command key → OS-specific command
    os_type = detect_os()  # "windows", "linux", "darwin"
    if cmd_key in COMMANDS_JSON:
        return COMMANDS_JSON[cmd_key].get(os_type, COMMANDS_JSON[cmd_key].get("linux"))
    
    return cmd_key  # fallback

# executor.py - Add the show_animations parameter:

def execute_command(parsed, show_animations=True):
    """
    parsed is tuple from parser:
    ("builtin", func, args:list) or ("shell", command_string)
    show_animations: whether to show processing/success animations
    """
    if not parsed:
        return

    kind = parsed[0]
    if kind == "builtin":
        func = parsed[1]
        args = parsed[2] if len(parsed) > 2 else []
        try:
            if show_animations:
                processing_animation()
            func(args)
            if show_animations:
                success_animation()
        except SystemExit:
            raise
        except Exception as e:
            if show_animations:
                box_print("Error", [str(e)], color="red")
            else:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
    elif kind == "shell":
        cmd = parsed[1]
        # detect if request to clear
        if cmd.strip().lower() in ("clear", "cls"):
            clear_screen()
            return
        try:
            proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            if out:
                if show_animations:
                    box_print(f"OUTPUT: {cmd}", out.splitlines(), color="green")
                else:
                    print(f"{Fore.GREEN}Output:{Style.RESET_ALL}")
                    print(out)
            if err:
                if show_animations:
                    box_print(f"ERROR: {cmd}", err.splitlines(), color="red")
                else:
                    print(f"{Fore.RED}Error:{Style.RESET_ALL}")
                    print(err)
            if not out and not err:
                if show_animations:
                    box_print("RESULT", ["(no output)"], color="yellow")
                else:
                    print(f"{Fore.YELLOW}(no output){Style.RESET_ALL}")
        except Exception as e:
            if show_animations:
                box_print("Execution error", [str(e)], color="red")
            else:
                print(f"{Fore.RED}Execution error: {e}{Style.RESET_ALL}")