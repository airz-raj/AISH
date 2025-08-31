from colorama import Fore

def typewriter(text, color=Fore.WHITE):
    print(color + text)

def print_colored_menu(options):
    for i, option in enumerate(options, 1):
        print(f"{Fore.LIGHTBLUE_EX}{i}) {Fore.LIGHTWHITE_EX}{option}")
    print(f"{Fore.LIGHTBLUE_EX}0) {Fore.LIGHTWHITE_EX}Exit")

def loading_dots(message, duration=1.0):
    print(message + "...")
