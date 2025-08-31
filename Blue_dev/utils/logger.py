# zomode/Blue_dev/utils/logger.py
from colorama import Fore, Style, init
init(autoreset=True)
def info(msg): print(f"{Fore.CYAN}[i]{Style.RESET_ALL} {msg}")
def good(msg): print(f"{Fore.GREEN}[+]{Style.RESET_ALL} {msg}")
def warn(msg): print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {msg}")
def error(msg): print(f"{Fore.RED}[-]{Style.RESET_ALL} {msg}")
def dim(msg): print(f"{Style.DIM}{msg}{Style.RESET_ALL}")
