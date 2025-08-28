# executor.py
import os
import subprocess
from typing import List, Optional
from colorama import Fore, Style
from utils import detect_os
import json

# Load patterns and command mappings
with open("patterns.json") as f:
    PATTERNS = json.load(f)

with open("commands.json") as f:
    COMMANDS_JSON = json.load(f)

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

def execute_command(parsed):
    """
    parsed is tuple from parser:
    ("builtin", func, args:list) or ("shell", command_string)
    """
    if not parsed:
        return

    kind = parsed[0]

    if kind == "builtin":
        func = parsed[1]
        args = parsed[2] if len(parsed) > 2 else []
        try:
            func(args)
        except SystemExit:
            raise
        except Exception as e:
            box_print("Error", [str(e)], color="red")

    elif kind == "shell":
        user_input = parsed[1]
        cmd = resolve_command(user_input)  # map NL → OS command

        if cmd.strip().lower() in ("clear", "cls"):
            clear_screen()
            return

        try:
            proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            if out:
                box_print(f"OUTPUT: {cmd}", out.splitlines(), color="green")
            if err:
                box_print(f"ERROR: {cmd}", err.splitlines(), color="red")
            if not out and not err:
                box_print("RESULT", ["(no output)"], color="yellow")
        except Exception as e:
            box_print("Execution error", [str(e)], color="red")
