#!/usr/bin/env python3
# aish.py
"""
AISH — integrated main program (UI/UX from animations.py + built-in useful commands).
Keeps the menu-driven UI and animations, but will run builtin functions from core_commands
or fall back to shell commands resolved via commands.json (OS-aware).
"""

import os
import json
import subprocess
import time
import random
from typing import Dict, Any, List, Optional
from voice_input import setup_voice_input, get_voice_input, is_voice_available, voice_status

from colorama import Fore, Style, init

# import animations (from the files your friend provided)
from animations import display_banner, glitch_animation, impact_animation

# local helpers & commands
from utils import resource_path, detect_os, run_subprocess
import core_commands
from autocomplete import create_advanced_autocompleter, get_advanced_input

def voice_to_menu_option(voice_text: str) -> Optional[str]:
    """Convert voice text to menu option number"""
    voice_text = voice_text.lower().strip()
    
    # Direct number match
    if voice_text in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        return voice_text
    
    # Word to number mapping
    voice_command_map = {
        "run": "1", "execute": "1", "command": "1", "launch": "1",
        "browse": "2", "list": "2", "commands": "2", "explore": "2",
        "history": "3", "log": "3", "past": "3", "previous": "3",
        "utilities": "4", "tools": "4", "built-in": "4", "functions": "4",
        "safety": "5", "check": "5", "secure": "5", "validate": "5",
        "help": "6", "tips": "6", "guide": "6", "assistance": "6",
        "exit": "7", "quit": "7", "stop": "7", "close": "7",
        "voice": "8", "speak": "8", "microphone": "8", "talk": "8"
    }
    
    for word, number in voice_command_map.items():
        if word in voice_text:
            return number
    
    # Try to extract number from speech
    number_words = {
        "one": "1", "two": "2", "three": "3", "four": "4", 
        "five": "5", "six": "6", "seven": "7", "eight": "8",
        "first": "1", "second": "2", "third": "3", "fourth": "4",
        "fifth": "5", "sixth": "6", "seventh": "7", "eighth": "8"
    }
    
    for word, number in number_words.items():
        if word in voice_text:
            return number
    
    return None

# Global autocompleter instance
aish_completer = None
# initialize colorama
init(autoreset=True)

# Load commands + patterns
def load_json_safe(fname: str) -> Dict[str, Any]:
    try:
        path = resource_path(fname)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

commands_json = load_json_safe("commands.json")
patterns_json = load_json_safe("patterns.json")

HISTORY_FILE = resource_path("history.json") if True else "history.json"  # resource_path returns base path
OS_NAME = detect_os()

# ----------------------------
# Small local animation wrappers (keeps UI/UX consistent)
# ----------------------------
def start_animation(duration: float = 1.0):
    spinner = ["|", "/", "-", "\\"]
    end = time.time() + duration
    msg = Fore.GREEN + "Launching AISH" + Style.RESET_ALL + " "
    while time.time() < end:
        for s in spinner:
            print("\r" + msg + s, end="", flush=True)
            time.sleep(0.06)
            if time.time() >= end:
                break
    print("\r" + " " * (len(msg) + 2) + "\r", end="", flush=True)

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

def blast_animation():
    try:
        impact_animation()
    except Exception:
        try:
            glitch_animation("ERROR", repeat=3, delay=0.06)
        except Exception:
            pass
        print(Fore.RED + "Invalid input." + Style.RESET_ALL)

def exit_animation():
    msg = Fore.MAGENTA + "Goodbye." + Style.RESET_ALL
    for i in range(3):
        print("\r" + msg + "." * i, end="", flush=True)
        time.sleep(0.25)
    print("\r" + " " * (len(msg) + 3) + "\r", end="", flush=True)

# ----------------------------
# history helpers
# ----------------------------
def append_history(entry: str):
    try:
        path = resource_path("history.json")
        # if resource_path returned a temp _MEIPASS path when packaged, write history next to exe instead
        if hasattr(__import__("sys"), "_MEIPASS"):
            # packaged: write to user folder instead
            path = os.path.join(os.path.expanduser("~"), ".aish_history.json")
        
        hist = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    # Handle both old (list of strings) and new (list of dicts) formats
                    if isinstance(loaded_data, list):
                        hist = loaded_data
            except Exception:
                hist = []
        
        # Convert any old string entries to new format when adding new ones
        if hist and isinstance(hist[0], str):
            # Convert old format to new format
            converted_hist = []
            for item in hist:
                if isinstance(item, str):
                    converted_hist.append({
                        "time": "Unknown time",
                        "entry": item
                    })
                else:
                    converted_hist.append(item)
            hist = converted_hist
        
        # Add new entry in consistent format
        hist.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "entry": entry
        })
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2)
    except Exception:
        # silent fail (history is convenience)
        pass

# ----------------------------
# grouped commands (UI browsing)
# ----------------------------
def grouped_commands(cmds: Dict[str, Any]) -> Dict[str, List]:
    groups = {
        "File Operations": [],
        "Development": [],
        "System": [],
        "Utilities": [],
        "Other": []
    }
    for name, desc in cmds.items():
        desc_str = ""
        if isinstance(desc, dict):
            desc_str = desc.get("description", "")
        else:
            desc_str = str(desc)
        lower_name = name.lower()
        if any(t in lower_name for t in ("ls", "cd", "mkdir", "rm", "touch", "mv", "zip", "unzip")) or "file" in desc_str.lower():
            groups["File Operations"].append((name, desc_str))
        elif any(t in lower_name for t in ("python", "node", "git", "make")):
            groups["Development"].append((name, desc_str))
        elif any(t in lower_name for t in ("top", "htop", "df", "free", "ps", "sysinfo", "battery")):
            groups["System"].append((name, desc_str))
        elif any(t in lower_name for t in ("curl", "wget", "ping", "scp", "scanport", "traceroute")):
            groups["Utilities"].append((name, desc_str))
        else:
            groups["Other"].append((name, desc_str))
    return groups

# ----------------------------
# decision: builtin or shell passthrough
# ----------------------------
# Add these helper functions at the top of aish.py (after imports)
def get_command_suggestions(user_input):
    """Get suggestions for wrong commands"""
    suggestions = []
    user_lower = user_input.lower()
    
    # Check patterns.json for keyword matches
    for pattern, command in patterns_json.items():
        if any(keyword in user_lower for keyword in pattern.split()):
            suggestions.append(f"Try: {pattern} → {command}")
    
    # Check commands.json
    for cmd in commands_json.keys():
        if cmd in user_lower:
            suggestions.append(f"Command available: {cmd}")
    
    # Check core commands
    for core_cmd in core_commands.COMMAND_REGISTRY.keys():
        if core_cmd in user_lower:
            suggestions.append(f"Built-in command: {core_cmd}")
    
    return suggestions[:5]  # Return top 5 suggestions

def show_suggestions(user_input):
    """Display helpful suggestions for wrong input"""
    suggestions = get_command_suggestions(user_input)
    
    if suggestions:
        print(Fore.YELLOW + "\n💡 Suggestions:" + Style.RESET_ALL)
        for i, suggestion in enumerate(suggestions, 1):
            print(Fore.CYAN + f"  {i}. {suggestion}" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "\n💡 Tip: Type 'help' to see available commands" + Style.RESET_ALL)
    
    # Show some general tips
    general_tips = [
        "Use 'menu' to return to main menu",
        "Type 'history' to see previous commands",
        "Try natural language like 'list files' or 'show system info'"
    ]
    
    print(Fore.MAGENTA + "\n📋 Quick Tips:" + Style.RESET_ALL)
    for tip in general_tips:
        print(Fore.LIGHTBLUE_EX + f"  • {tip}" + Style.RESET_ALL)

# Replace the resolve_and_run function with this enhanced version:
def resolve_and_run(raw_input: str):
    s = raw_input.strip()
    if not s:
        blast_animation()
        print(Fore.YELLOW + "Please enter a command" + Style.RESET_ALL)
        return

    # Handle help command
    if s.lower() in ['help', '?', 'menu']:
        show_help_menu()
        return

    # Handle clear screen
    if s.lower() in ['clear', 'cls']:
        os.system("cls" if OS_NAME == "windows" else "clear")
        return

    # quick pattern match (exact)
    key = None
    lowered = s.lower()
    if lowered in patterns_json:
        key = patterns_json[lowered]

    # if a pattern maps to a builtin command name present in core_commands registry
    if key and key in core_commands.COMMAND_REGISTRY:
        func = core_commands.COMMAND_REGISTRY[key]
        try:
            processing_animation()
            func([])
            success_animation()
            append_history(s)
            return
        except Exception as e:
            blast_animation()
            print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
            show_suggestions(s)
            return

    # direct builtin (first token)
    tokens = s.split()
    head = tokens[0].lower()
    tail = tokens[1:]
    if head in core_commands.COMMAND_REGISTRY:
        func = core_commands.COMMAND_REGISTRY[head]
        try:
            processing_animation()
            func(tail)
            success_animation()
            append_history(s)
            return
        except Exception as e:
            blast_animation()
            print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
            show_suggestions(s)
            return

    # if head matches commands.json keys (shell mapping), build os-aware command
    if head in commands_json:
        entry = commands_json[head]
        cmd_template = entry.get(OS_NAME) if isinstance(entry, dict) else entry
        if not cmd_template and isinstance(entry, dict):
            cmd_template = entry.get("linux") or ""
        cmd_to_run = f"{cmd_template} {' '.join(tail)}".strip()
        try:
            processing_animation()
            run_shell_command(cmd_to_run)
            success_animation()
            append_history(s)
            return
        except Exception as e:
            blast_animation()
            print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
            show_suggestions(s)
            return

    # fallback: treat entire input as shell passthrough
    try:
        processing_animation()
        result = run_shell_command(s)
        if result != 0:  # Command failed
            show_suggestions(s)
        else:
            success_animation()
        append_history(s)
    except Exception as e:
        blast_animation()
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
        show_suggestions(s)

# Add this helper function for help menu
def show_help_menu():
    """Show comprehensive help menu"""
    print(Fore.CYAN + "\n" + "="*60 + Style.RESET_ALL)
    print(Fore.MAGENTA + "🤖 AISH HELP MENU" + Style.RESET_ALL)
    print(Fore.CYAN + "="*60 + Style.RESET_ALL)
    
    print(Fore.YELLOW + "\n📋 Available Command Types:" + Style.RESET_ALL)
    print(Fore.GREEN + "  • Built-in commands (sysinfo, battery, zip, etc.)")
    print(Fore.GREEN + "  • Shell commands (ls, pwd, mkdir, etc.)")
    print(Fore.GREEN + "  • Natural language patterns")
    
    print(Fore.YELLOW + "\n🎯 Natural Language Examples:" + Style.RESET_ALL)
    nl_examples = [
        "list all files",
        "show system info", 
        "battery status",
        "clear screen",
        "zip folder"
    ]
    for example in nl_examples:
        if example in patterns_json:
            print(Fore.CYAN + f"  {example} → {patterns_json[example]}" + Style.RESET_ALL)
    
    print(Fore.YELLOW + "\n⚡ Quick Commands:" + Style.RESET_ALL)
    print(Fore.LIGHTBLUE_EX + "  help" + Style.RESET_ALL + " - Show this menu")
    print(Fore.LIGHTBLUE_EX + "  menu" + Style.RESET_ALL + " - Return to main menu")
    print(Fore.LIGHTBLUE_EX + "  history" + Style.RESET_ALL + " - Show command history")
    print(Fore.LIGHTBLUE_EX + "  clear" + Style.RESET_ALL + " - Clear screen")
    
    print(Fore.CYAN + "\n" + "="*60 + Style.RESET_ALL)
    
    
def voice_listening_animation(duration: float = 3.0):
    """Animation while listening for voice"""
    frames = ["🎤   ", "🎤.  ", "🎤.. ", "🎤..."]
    end_time = time.time() + duration
    
    while time.time() < end_time:
        for frame in frames:
            if time.time() >= end_time:
                break
            print(f"\r{Fore.CYAN}{frame}{Style.RESET_ALL}", end='', flush=True)
            time.sleep(0.3)
    print("\r" + " " * 20 + "\r", end='', flush=True)

def voice_processing_animation():
    """Animation while processing voice"""
    frames = ["🔍   ", "🔍.  ", "🔍.. ", "🔍..."]
    for _ in range(2):  # Show for about 2 seconds
        for frame in frames:
            print(f"\r{Fore.BLUE}{frame}{Style.RESET_ALL}", end='', flush=True)
            time.sleep(0.2)
    print("\r" + " " * 20 + "\r", end='', flush=True)
    

    

def run_shell_command(cmd: str):
    """
    Runs an arbitrary shell command (shell=True) using subprocess.run and prints output.
    We run it in the current terminal so user sees stdout/stderr directly.
    """
    # handle clear specially to keep cross-platform behavior
    low = cmd.strip().lower()
    if low in ("clear", "cls"):
        os.system("cls" if OS_NAME == "windows" else "clear")
        return
    # run and stream output
    try:
        proc = subprocess.run(cmd, shell=True)
        return proc.returncode
    except Exception as e:
        raise

# ----------------------------
# Menu loop
# ----------------------------
# Replace the entire main() function with this enhanced version:
# aish.py
# Replace the main loop with this improved structure:

def main():
    global aish_completer
    # Initialize autocompleter
    aish_completer = create_advanced_autocompleter(commands_json, patterns_json, core_commands)
    voice_handler = setup_voice_input()
    
    # Show voice status
    if is_voice_available():
        print(Fore.CYAN + "🎤 " + voice_status() + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "🔇 " + voice_status() + Style.RESET_ALL)
        print(Fore.YELLOW + "   Install: pip install SpeechRecognition pyaudio" + Style.RESET_ALL)
    
    migrate_history_format()
    # show banner and small start animation
    try:
        display_banner()
    except Exception:
        # fallback banner
        print(Fore.CYAN + "AISH - AI Shell Helper" + Style.RESET_ALL)
        print(Fore.CYAN + "By AIRZ01" + Style.RESET_ALL)
    start_animation()

    while True:
        try:
            print(Fore.CYAN + Style.BRIGHT + "\n=== AISH – Main Menu ===" + Style.RESET_ALL)
            print(Fore.YELLOW + "1)" + Style.RESET_ALL + " Run command (NL or direct)")
            print(Fore.YELLOW + "2)" + Style.RESET_ALL + " Browse available commands")
            print(Fore.YELLOW + "3)" + Style.RESET_ALL + " View command history")
            print(Fore.YELLOW + "4)" + Style.RESET_ALL + " Built-in utilities")
            print(Fore.YELLOW + "5)" + Style.RESET_ALL + " Safety check command")
            print(Fore.YELLOW + "6)" + Style.RESET_ALL + " Help & tips")
            print(Fore.YELLOW + "7)" + Style.RESET_ALL + " Exit")
            print(Fore.YELLOW + "8)" + Style.RESET_ALL + " Voice input mode")

            choice = get_advanced_input(Fore.GREEN + "Choose an option (1-8): " + Style.RESET_ALL, aish_completer).strip()

            # Handle voice input option separately
            if choice == "8":
                if not is_voice_available():
                    print(Fore.RED + "Voice input not available. Install requirements first." + Style.RESET_ALL)
                    print(Fore.YELLOW + "Run: pip install SpeechRecognition pyaudio" + Style.RESET_ALL)
                    continue
                
                print(Fore.CYAN + "\n🎤 Voice Input Mode" + Style.RESET_ALL)
                print("Say menu options like 'run command', 'browse commands', or 'exit'")
                print("Or speak natural language commands directly")
                
                voice_text = get_voice_input("What would you like to do?")
                
                if voice_text is None:
                    print("No voice input received or listening timed out")
                    continue
                
                if voice_text.lower() in ['cancel', 'stop', 'quit', 'exit']:
                    print("Voice input cancelled")
                    continue
                
                # Try to convert to menu option first
                menu_option = voice_to_menu_option(voice_text)
                if menu_option and menu_option != "cancel":
                    print(f"Voice command: '{voice_text}' → Option {menu_option}")
                    # Process the menu option immediately instead of setting choice
                    process_menu_option(menu_option)
                else:
                    # Treat as direct command
                    print(f"Executing voice command: {voice_text}")
                    resolve_and_run(voice_text)
                    # Add a small delay to show results before returning to menu
                    time.sleep(1)
                continue  # Go back to main menu after processing

            # Process regular menu choices
            process_menu_option(choice)

        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n\nUse option 7 or type 'exit' to quit properly." + Style.RESET_ALL)
            continue
        except Exception as e:
            print(Fore.RED + f"Unexpected error: {e}" + Style.RESET_ALL)
            print(Fore.YELLOW + "The program will continue running..." + Style.RESET_ALL)
            continue

# ADD THIS NEW FUNCTION to handle menu options:
def process_menu_option(choice: str):
    """Process menu selection and execute the corresponding action"""
    if choice == "1":
        print(Fore.CYAN + "Press 'v' for voice input or type your command" + Style.RESET_ALL)
        user_input = get_advanced_input("\nEnter command (or 'v' for voice): ", aish_completer).strip()
        
        if user_input.lower() == 'v':
            if not is_voice_available():
                print(Fore.RED + "Voice input not available" + Style.RESET_ALL)
                return
                
            voice_text = get_voice_input("Speak your command")
            if voice_text and voice_text.lower() != 'cancel':
                user_input = voice_text
                print(f"Voice command: {user_input}")
        
        if not user_input:
            print(Fore.YELLOW + "Please enter a command. Type 'help' for options." + Style.RESET_ALL)
            return
        
        resolve_and_run(user_input)

    elif choice == "2":
        groups = grouped_commands(commands_json)
        for group, cmds in groups.items():
            print(Fore.MAGENTA + f"\n{group}:" + Style.RESET_ALL)
            for cmd, desc in cmds:
                print(Fore.CYAN + f"  {cmd}" + Style.RESET_ALL + (f" – {desc}" if desc else ""))
        
        # Show natural language examples
        print(Fore.MAGENTA + "\n💬 Natural Language Examples:" + Style.RESET_ALL)
        nl_examples = list(patterns_json.keys())[:5]  # First 5 examples
        for example in nl_examples:
            print(Fore.CYAN + f"  {example}" + Style.RESET_ALL + f" → {patterns_json[example]}")

    elif choice == "3":
        # VIEW COMMAND HISTORY
        history_file = resource_path("history.json")
        altpath = os.path.join(os.path.expanduser("~"), ".aish_history.json")
        usepath = altpath if (os.path.exists(altpath) and not os.path.exists(history_file)) else history_file
        
        if os.path.exists(usepath):
            try:
                with open(usepath, "r", encoding="utf-8") as hf:
                    hist = json.load(hf)
                
                if not hist:
                    print(Fore.YELLOW + "No history yet. Run some commands first!" + Style.RESET_ALL)
                else:
                    print(Fore.MAGENTA + "\n📜 Command History (recent first):" + Style.RESET_ALL)
                    
                    # Handle both old format (strings) and new format (dictionaries)
                    for i, h in enumerate(reversed(hist[-10:]), 1):  # Show last 10
                        if isinstance(h, dict):
                            # New format: dictionary with time and entry
                            t = h.get("time", "Unknown time")
                            e = h.get("entry", "Unknown command")
                        else:
                            # Old format: simple string
                            t = "Unknown time"
                            e = str(h)
                        
                        print(Fore.CYAN + f"  {i}. {t} — {e}" + Style.RESET_ALL)
                        
            except Exception as e:
                print(Fore.RED + f"Error reading history: {e}" + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + "No history file found. Commands will be saved after you run them." + Style.RESET_ALL)

    elif choice == "4":
        print(Fore.MAGENTA + "\n🔧 Built-in Utilities:" + Style.RESET_ALL)
        for k in sorted(core_commands.COMMAND_REGISTRY.keys()):
            doc = core_commands.COMMAND_REGISTRY[k].__doc__ or "No description"
            print(Fore.CYAN + f"  {k}" + Style.RESET_ALL + f" – {doc.split('—')[0].strip()}")
        
        print(Fore.YELLOW + "\n💡 Usage: Just type the command name in option 1" + Style.RESET_ALL)

    elif choice == "5":
        try:
            import safety
            target = get_advanced_input("Enter command to safety check: ", aish_completer).strip()
            if not target:
                print(Fore.YELLOW + "Please enter a command to check" + Style.RESET_ALL)
                return
            
            result = safety.check(target)
            print(f"\n🔒 Safety Check Results:")
            print(f"Command: {result['command']}")
            print(f"Status: {result['message']}")
            
            if result['suggestions']:
                print(f"\n💡 Suggestions:")
                for i, suggestion in enumerate(result['suggestions'], 1):
                    print(f"  {i}. {suggestion}")
            
            if result['safe']:
                print(Fore.GREEN + "\n✅ This command appears safe" + Style.RESET_ALL)
            else:
                print(Fore.RED + "\n❌ WARNING: This command is dangerous!" + Style.RESET_ALL)
                
        except Exception as e:
            print(Fore.RED + f"Safety check error: {e}" + Style.RESET_ALL)
            print(Fore.YELLOW + "Make sure safety.py is in the same directory" + Style.RESET_ALL)

    elif choice == "6":
        show_help_menu()

    elif choice == "7":
        exit_animation()
        exit(0)  # Exit the program completely

    else:
        print(Fore.RED + "Invalid option! Please choose 1-8." + Style.RESET_ALL)
        print(Fore.YELLOW + "💡 Tip: Type the number only (e.g., '1' for Run command)" + Style.RESET_ALL)


def migrate_history_format():
    """Convert old history format to new format"""
    try:
        path = resource_path("history.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            
            # Check if migration is needed (old format is list of strings)
            if old_data and isinstance(old_data, list) and isinstance(old_data[0], str):
                new_data = []
                for item in old_data:
                    new_data.append({
                        "time": "Unknown time",
                        "entry": item
                    })
                
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2)
                print(Fore.YELLOW + "History format migrated to new format" + Style.RESET_ALL)
                
    except Exception:
        pass 

if __name__ == "__main__":
    main()
    migrate_history_format()
