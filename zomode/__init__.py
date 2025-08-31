from . import osint
from . import tor_integration
import time
import sys
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# ----------------- Terminal helpers -----------------
def typewriter(text, delay=0.01, color=Fore.LIGHTWHITE_EX):
    for ch in text:
        sys.stdout.write(f"{color}{ch}")
        sys.stdout.flush()
        time.sleep(delay)
    print()

def print_colored_menu(options):
    """Ubuntu/Debian style colored menu"""
    for idx, opt in enumerate(options, 1):
        print(f"{Fore.LIGHTRED_EX}{idx}) {Fore.LIGHTWHITE_EX}{opt}")
    print(f"{Fore.LIGHTRED_EX}0) {Fore.LIGHTWHITE_EX}Back")

def loading_dots(message="Loading", duration=2.0):
    """Simple loading animation with dots."""
    dots = ["   ", ".  ", ".. ", "..."]
    end_time = time.time() + duration
    idx = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r{Fore.LIGHTGREEN_EX}{message}{dots[idx % len(dots)]}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.6)
        idx += 1
    print("\r", end="")  # clear line after done

def startup_animation(message="Entering Z-Omode"):
    typewriter(message + "...", color=Fore.LIGHTCYAN_EX)
    loading_dots("Starting", duration=1.0)

# ----------------- Z-Omode Menu -----------------
def zomode_menu(args=None):
    startup_animation()
    while True:
        typewriter("\n=== Z-Omode ===", color=Fore.LIGHTRED_EX)
        options = ["OSINT (OSINT Toolkit)", "Tor Integration", "Ter-Bro (coming soon)"]
        print_colored_menu(options)

        choice = input(Fore.LIGHTCYAN_EX + "Select an option: " + Style.RESET_ALL).strip()
        if choice == "0":
            break
        elif choice == "1":
            osint.osint_menu()
        elif choice == "2":
            tor_menu()
        elif choice == "3":
            typewriter("⚠ Ter-Bro is not implemented yet.", color=Fore.YELLOW)
        else:
            typewriter("❌ Invalid choice", color=Fore.LIGHTRED_EX)

# ----------------- Tor Menu -----------------
def tor_menu():
    startup_animation("Tor Integration Menu")
    while True:
        typewriter("\n=== Tor Integration ===", color=Fore.LIGHTRED_EX)
        options = [
            "Route command through Tor (torify)",
            "Start Tor Browser",
            "Check Tor Status",
            "Install Tor (instructions)",
            "Run command with ProxyChains",
            "Enable Anonsurf (system-wide)",
            "Disable Anonsurf (system-wide)"
        ]
        print_colored_menu(options)

        choice = input(Fore.LIGHTCYAN_EX + "Select an option: " + Style.RESET_ALL).strip()
        if choice == "0":
            break
        elif choice == "1":
            cmd = input("Enter command to run through Tor: ").split()
            loading_dots("Executing", duration=1.0)  # changed to 1 sec
            print(tor_integration.torify_cmd(cmd))
        elif choice == "2":
            loading_dots("Launching Tor Browser", duration=1.0)
            print(tor_integration.tor_browser_cmd([]))
        elif choice == "3":
            loading_dots("Checking Tor Status", duration=1.0)
            print(tor_integration.tor_status_cmd([]))
        elif choice == "4":
            loading_dots("Opening Install Instructions", duration=1.0)
            print(tor_integration.tor_install_cmd([]))
        elif choice == "5":
            cmd = input("Enter command to run with ProxyChains: ").split()
            loading_dots("Executing with ProxyChains", duration=1.0)
            print(tor_integration.tor_proxychains_cmd(cmd))
        elif choice == "6":
            loading_dots("Enabling Anonsurf", duration=1.0)
            print(tor_integration.tor_anonsurf_start_cmd([]))
        elif choice == "7":
            loading_dots("Disabling Anonsurf", duration=1.0)
            print(tor_integration.tor_anonsurf_stop_cmd([]))
        else:
            typewriter("❌ Invalid choice", color=Fore.LIGHTRED_EX)
