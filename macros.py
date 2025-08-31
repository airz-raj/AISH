"""
Macro system for AISH - allows creating and running command sequences
"""

import json
import os
from typing import Dict, List
from colorama import Fore, Style

def get_macros_path() -> str:
    """Get the path to the macros storage file (inside AISH folder)"""
    base_dir = os.path.dirname(os.path.abspath(__file__))  # folder where macros.py lives
    return os.path.join(base_dir, "macros.json")


def load_macros() -> Dict[str, List[str]]:
    """Load macros from storage file"""
    macros_path = get_macros_path()
    if os.path.exists(macros_path):
        try:
            with open(macros_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"{Fore.RED}Error loading macros: {e}{Style.RESET_ALL}")
    return {}

def save_macros(macros: Dict[str, List[str]]):
    """Save macros to storage file (with atomic write for safety)"""
    try:
        macros_path = get_macros_path()
        tmp_path = macros_path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(macros, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, macros_path)  # atomic save
    except Exception as e:
        print(f"{Fore.RED}Error saving macros: {e}{Style.RESET_ALL}")

def create_macro(macro_name: str, commands: List[str]):
    """Create or update a macro"""
    macro_name = macro_name.strip().lower()
    if not macro_name:
        print(f"{Fore.RED}✗ Macro name cannot be empty{Style.RESET_ALL}")
        return
    if not commands:
        print(f"{Fore.RED}✗ No commands provided for macro '{macro_name}'{Style.RESET_ALL}")
        return
    
    macros = load_macros()
    macros[macro_name] = commands
    save_macros(macros)
    print(f"{Fore.GREEN}✓ Macro '{macro_name}' created with {len(commands)} commands{Style.RESET_ALL}")

def get_macro(macro_name: str) -> List[str]:
    """Get commands for a macro"""
    return load_macros().get(macro_name.strip().lower(), [])

def list_macros() -> Dict[str, List[str]]:
    """List all available macros"""
    return load_macros()

def delete_macro(macro_name: str):
    """Delete a macro"""
    macro_name = macro_name.strip().lower()
    macros = load_macros()
    if macro_name in macros:
        del macros[macro_name]
        save_macros(macros)
        print(f"{Fore.GREEN}✓ Macro '{macro_name}' deleted{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ Macro '{macro_name}' not found{Style.RESET_ALL}")

def run_macro(macro_name: str, execute_function):
    """Run a macro by executing each command in sequence"""
    macro_name = macro_name.strip().lower()
    commands = get_macro(macro_name)
    
    if not commands:
        print(f"{Fore.RED}✗ Macro '{macro_name}' not found{Style.RESET_ALL}")
        return False
    
    print(f"{Fore.CYAN}🚀 Running macro '{macro_name}' ({len(commands)} commands)...{Style.RESET_ALL}")
    
    success_count = 0
    for i, command in enumerate(commands, 1):
        print(f"{Fore.YELLOW}[{i}/{len(commands)}] Executing: {command}{Style.RESET_ALL}")
        try:
            execute_function(command)
            success_count += 1
        except Exception as e:
            print(f"{Fore.RED}❌ Command failed: {e}{Style.RESET_ALL}")
    
    print(f"{Fore.GREEN}✓ Macro completed: {success_count}/{len(commands)} commands successful{Style.RESET_ALL}")
    return success_count == len(commands)
