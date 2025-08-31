# menu.py
from colorama import init, Fore, Style
import sys
import time
import os
from colorama import Fore, Style

# Import the key generation flow from key_generation.py
from .key_generation import generate_key_flow

init(autoreset=True)

def _typewriter(text, delay=0.01, color=Fore.LIGHTWHITE_EX):
    for ch in text:
        sys.stdout.write(f"{color}{ch}")
        sys.stdout.flush()
        time.sleep(delay)
    print(Style.RESET_ALL, end="")

def _loading_dots(message="Loading", duration=0.8):
    dots = ["   ", ".  ", ".. ", "..."]
    start = time.time()
    idx = 0
    while time.time() - start < duration:
        sys.stdout.write(f"\r{Fore.LIGHTGREEN_EX}{message}{dots[idx % len(dots)]}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.5)
        idx += 1
    print("\r", end="")

def launch_web_access():
    """
    Placeholder for Web access (Django + OpenCV login).
    Hook your web app here later (CLI entrypoint or HTTP call).
    """
    _typewriter("Opening Web Access (Django + OpenCV login) ...", color=Fore.CYAN)
    _loading_dots("Preparing")
    print(Fore.YELLOW + "\n[Placeholder] Plug your web project here." + Style.RESET_ALL)

def built_env():
    print(Fore.MAGENTA + "[Placeholder] Built-env will be added later." + Style.RESET_ALL)

def stmp_database():
    print(Fore.MAGENTA + "[Placeholder] STMP and DATABASE (Temp.) will be added later." + Style.RESET_ALL)

def gmode_menu(args=None):
    _typewriter("Entering GMode...", color=Fore.LIGHTCYAN_EX)
    _loading_dots("Starting", duration=0.8)
    while True:
        _typewriter("\n=== GMode ===\n", color=Fore.LIGHTRED_EX)
        options = [
            "1) Key Generation",
            "2) Built-env",
            "3) STMP and DATABASE (Temp.)",
            "0) Exit"
        ]
        for opt in options:
            left, right = opt.split(")", 1)
            print(Fore.YELLOW + left + ")" + Style.RESET_ALL + right)

        choice = input("Select an option (0-3): ").strip()
        if choice == "1":
            generate_key_flow()  # <-- function from gmode.py
        elif choice == "2":
            built_env()
        elif choice == "3":
            stmp_database()
        elif choice == "0":
            print(Fore.CYAN + "Leaving GMode..." + Style.RESET_ALL)
            break
        else:
            print(Fore.RED + "Invalid option. Choose 0-3." + Style.RESET_ALL)

