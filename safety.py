# safety.py
"""
Enhanced safety check with better pattern matching and suggestions
"""

import re
from typing import List, Dict, Tuple

# Expanded list of dangerous patterns with descriptions
DANGEROUS_PATTERNS = {
    "rm -rf /": "DANGEROUS: Deletes all files on system",
    "rm -rf /*": "DANGEROUS: Deletes all files on system",
    ":(){:|:&};:": "DANGEROUS: Fork bomb - crashes system",
    "mkfs": "DANGEROUS: Formats filesystem",
    "dd if=/dev/random": "DANGEROUS: Overwrites with random data",
    "chmod -R 000 /": "DANGEROUS: Makes all files inaccessible",
    "> /dev/sda": "DANGEROUS: Overwrites disk device",
    "mv / /dev/null": "DANGEROUS: Moves root to null device",
}

# Warning patterns (less dangerous but should be confirmed)
WARNING_PATTERNS = {
    "rm -rf": "WARNING: Recursive force delete",
    "rm -r": "WARNING: Recursive delete",
    "shutdown": "WARNING: System shutdown",
    "reboot": "WARNING: System reboot",
    "poweroff": "WARNING: Power off",
    "kill -9": "WARNING: Force kill process",
    ">": "WARNING: Output redirection",
}

def is_safe(cmd: str) -> Tuple[bool, str, List[str]]:
    """
    Check if command is safe
    Returns: (is_safe, message, suggestions)
    """
    cmd_lower = cmd.strip().lower()
    
    # Check for dangerous patterns
    for pattern, description in DANGEROUS_PATTERNS.items():
        if pattern.lower() in cmd_lower:
            return False, description, get_safety_suggestions(cmd)
    
    # Check for warning patterns
    for pattern, description in WARNING_PATTERNS.items():
        if pattern.lower() in cmd_lower:
            return True, f"CAUTION: {description}", get_safety_suggestions(cmd)
    
    # Check for suspicious patterns
    suspicious_patterns = [
        (r"rm.*-.*f", "Force delete without confirmation"),
        (r"rm.*/.*", "Deleting from root directory"),
        (r"chmod.*0+", "Removing all permissions"),
        (r">.*dev", "Redirecting to device files"),
    ]
    
    for pattern, description in suspicious_patterns:
        if re.search(pattern, cmd_lower):
            return True, f"REVIEW: {description}", get_safety_suggestions(cmd)
    
    return True, "SAFE: Command appears safe", []

def get_safety_suggestions(cmd: str) -> List[str]:
    """Get safety suggestions for a command"""
    suggestions = []
    cmd_lower = cmd.lower()
    
    if "rm " in cmd_lower and "-i" not in cmd_lower:
        suggestions.append("Add '-i' for interactive confirmation before deleting")
    
    if "rm " in cmd_lower and not any(x in cmd_lower for x in ["./", "~/", "/home/"]):
        suggestions.append("Specify full path to avoid accidental deletion")
    
    if ">" in cmd_lower and not any(x in cmd_lower for x in [".txt", ".log", ".json"]):
        suggestions.append("Consider using file extension to avoid overwriting devices")
    
    if "chmod" in cmd_lower and "777" in cmd_lower:
        suggestions.append("Use more restrictive permissions (e.g., 755 instead of 777)")
    
    if not suggestions:
        suggestions.append("Double-check the command before executing")
        suggestions.append("Use '--dry-run' option if available")
        suggestions.append("Test in a safe environment first")
    
    return suggestions

def check(cmd: str) -> Dict[str, any]:
    """
    Main safety check function
    Returns: {"safe": bool, "message": str, "suggestions": list}
    """
    safe, message, suggestions = is_safe(cmd)
    
    return {
        "safe": safe,
        "message": message,
        "suggestions": suggestions,
        "command": cmd
    }

# Additional helper function for interactive safety check
def interactive_safety_check(cmd: str) -> bool:
    """
    Interactive safety check with user confirmation
    Returns: True if user confirms, False otherwise
    """
    result = check(cmd)
    
    print(f"\n🔒 Safety Check for: {cmd}")
    print(f"Status: {result['message']}")
    
    if result['suggestions']:
        print("\n💡 Suggestions:")
        for i, suggestion in enumerate(result['suggestions'], 1):
            print(f"  {i}. {suggestion}")
    
    if not result['safe']:
        print(f"\n❌ BLOCKED: This command is too dangerous to execute")
        return False
    
    if "WARNING" in result['message'] or "REVIEW" in result['message']:
        confirmation = input("\n⚠️  Continue anyway? (y/N): ").strip().lower()
        return confirmation == 'y'
    
    return True