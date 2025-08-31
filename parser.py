# parser.py
import json
import re
from difflib import get_close_matches
from typing import Optional, Tuple, List
from utils import resource_path
from core_commands import COMMAND_REGISTRY
from core_commands import macro_help_cmd 

def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def load_json(path: str):
    with open(resource_path(path), 'r', encoding='utf-8') as f:
        return json.load(f)

def get_parsing_suggestions(user_input: str, patterns_json: dict, commands_json: dict) -> List[str]:
    """Get suggestions for parsing errors"""
    suggestions = []
    user_lower = user_input.lower()
    
    # Check for similar patterns
    all_patterns = list(patterns_json.keys())
    similar_patterns = [p for p in all_patterns if any(word in user_lower for word in p.split())]
    
    for pattern in similar_patterns[:3]:  # Top 3 matches
        suggestions.append(f"Try: '{pattern}' → {patterns_json[pattern]}")
    
    # Check for command keywords
    for cmd in commands_json.keys():
        if cmd in user_lower:
            suggestions.append(f"Command available: {cmd}")
    
    if not suggestions:
        suggestions.append("Type 'help' to see available commands")
        suggestions.append("Try simple commands like 'list files' or 'sysinfo'")
    
    return suggestions

def parse_command(user_input: str, commands_json: dict, patterns_json: dict, current_os: str):
    ui = normalize(user_input)
    if ui == "":
        return None

    # 0. Check for macro commands first
    if ui.startswith("macro "):
        macro_parts = ui.split()
        if len(macro_parts) >= 2:
            macro_action = macro_parts[1]
            macro_args = macro_parts[2:] if len(macro_parts) > 2 else []
            
            # Map to appropriate macro command
            if macro_action in ["create", "run", "list", "delete", "help"]:
                return ("builtin", COMMAND_REGISTRY.get(f"macro {macro_action}", macro_help_cmd), macro_args)

def parse_command(user_input: str, commands_json: dict, patterns_json: dict, current_os: str):
    ui = normalize(user_input)
    if ui == "":
        return None

    # 1. FIRST check patterns: exact match (this should be the first check)
    # Convert patterns to lowercase for case-insensitive matching
    ui_lower = ui.lower()
    
    if ui_lower.startswith("create macro"):
        macro_name = ui_lower[12:].strip()
        return ("builtin", COMMAND_REGISTRY["macro_create"], [macro_name])
    elif ui_lower.startswith("make macro"):
        macro_name = ui_lower[10:].strip()
        return ("builtin", COMMAND_REGISTRY["macro_create"], [macro_name])
    elif ui_lower.startswith("run macro"):
        macro_name = ui_lower[9:].strip()
        return ("builtin", COMMAND_REGISTRY["macro_run"], [macro_name])
    elif ui_lower.startswith("execute macro"):
        macro_name = ui_lower[13:].strip()
        return ("builtin", COMMAND_REGISTRY["macro_run"], [macro_name])
    elif ui_lower.startswith("list macros"):
        return ("builtin", COMMAND_REGISTRY["macro_list"], [])
    elif ui_lower.startswith("show macros"):
        return ("builtin", COMMAND_REGISTRY["macro_list"], [])
    elif ui_lower.startswith("delete macro"):
        macro_name = ui_lower[12:].strip()
        return ("builtin", COMMAND_REGISTRY["macro_delete"], [macro_name])
    elif ui_lower.startswith("remove macro"):
        macro_name = ui_lower[12:].strip()
        return ("builtin", COMMAND_REGISTRY["macro_delete"], [macro_name])
    
    if ui_lower in patterns_json:
        key = patterns_json[ui_lower]
        # If pattern maps to builtin
        if key in COMMAND_REGISTRY:
            return ("builtin", COMMAND_REGISTRY[key], [])
        # If pattern maps to shell command key
        if key in commands_json:
            cmd = commands_json[key].get(current_os, commands_json[key].get("linux"))
            return ("shell", cmd)

    # 2. If the exact first token matches a builtin or command key or pattern
    parts = ui.split()
    head = parts[0].lower() if parts else ""
    tail = parts[1:] if len(parts) > 1 else []

    # builtin exact
    if head in COMMAND_REGISTRY:
        return ("builtin", COMMAND_REGISTRY[head], tail)

    # pattern head exact (check if first word matches any pattern)
    if head in patterns_json:
        mapped = patterns_json[head]
        if mapped in COMMAND_REGISTRY:
            return ("builtin", COMMAND_REGISTRY[mapped], tail)
        if mapped in commands_json:
            cmd = commands_json[mapped].get(current_os, commands_json[mapped].get("linux"))
            full = f"{cmd} {' '.join(tail)}".strip()
            return ("shell", full)

    # commands.json exact
    if head in commands_json:
        base = commands_json[head].get(current_os, commands_json[head].get("linux"))
        full = f"{base} {' '.join(tail)}".strip()
        return ("shell", full)

    # 3. fuzzy match for patterns then commands
    cand = get_close_matches(ui_lower, patterns_json.keys(), n=1, cutoff=0.6)  # Lower cutoff for better matching
    if cand:
        key = patterns_json[cand[0]]
        if key in COMMAND_REGISTRY:
            return ("builtin", COMMAND_REGISTRY[key], [])
        if key in commands_json:
            cmd = commands_json[key].get(current_os, commands_json[key].get("linux"))
            return ("shell", cmd)

    cand_cmd = get_close_matches(head, commands_json.keys(), n=1, cutoff=0.6)
    if cand_cmd:
        base = commands_json[cand_cmd[0]].get(current_os, commands_json[cand_cmd[0]].get("linux"))
        full = f"{base} {' '.join(tail)}".strip()
        return ("shell", full)
    # parser.py - Add this right after the patterns check:

    # Special handling for macro commands
    macro_prefixes = ["create macro", "make macro", "run macro", "execute macro", 
                     "list macros", "show macros", "delete macro", "remove macro"]
    
    for prefix in macro_prefixes:
        if ui_lower.startswith(prefix):
            remaining = ui_lower[len(prefix):].strip()
            args = [remaining] if remaining else []
            
            if prefix in ["create macro", "make macro"]:
                return ("builtin", COMMAND_REGISTRY["macro_create"], args)
            elif prefix in ["run macro", "execute macro"]:
                return ("builtin", COMMAND_REGISTRY["macro_run"], args)
            elif prefix in ["list macros", "show macros"]:
                return ("builtin", COMMAND_REGISTRY["macro_list"], args)
            elif prefix in ["delete macro", "remove macro"]:
                return ("builtin", COMMAND_REGISTRY["macro_delete"], args)

    # 4. last-ditch: treat whole input as shell passthrough
    return ("shell", ui)