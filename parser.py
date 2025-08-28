# parser.py
import json
import re
from difflib import get_close_matches
from typing import Optional, Tuple, List
from utils import resource_path
from core_commands import COMMAND_REGISTRY

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

    # 1. FIRST check patterns: exact match (this should be the first check)
    # Convert patterns to lowercase for case-insensitive matching
    ui_lower = ui.lower()
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

    # 4. last-ditch: treat whole input as shell passthrough
    return ("shell", ui)