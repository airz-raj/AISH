import re, os
import json
from utils import detect_os, resource_path

# load commands.json for cross-platform
def load_commands():
    try:
        with open(resource_path("commands.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

COMMANDS = load_commands()
OS_NAME = detect_os()

class AishContext:
    def __init__(self):
        self.history = []
        self.entities = {
            "last_files": [],
            "last_dir": None,
            "last_host": None,
            "last_process": None,
            "last_output": None
        }

    def update(self, command, result=None, type_="command", entities=None, exit_code=0):
        entry = {
            "command": command,
            "result": result,
            "type": type_,
            "entities": entities or {},
            "exit_code": exit_code
        }
        self.history.append(entry)

        if entities:
            for k, v in entities.items():
                self.entities[f"last_{k}"] = v
        if result:
            self.entities["last_output"] = result

    def last_command(self, n=1):
        """Return the nth last history entry dict."""
        return self.history[-n] if len(self.history) >= n else None

    def last_cmd_str(self, n=1):
        """Return just the command string from history."""
        entry = self.last_command(n)
        return entry["command"] if entry else None


def resolve_with_context(user_input: str, ctx: AishContext) -> str:
    """
    Expand pronouns, synonyms, and modifiers based on context.
    Cross-platform safe (Linux/macOS vs Windows).
    """
    text = user_input.strip().lower()
    last_cmd = ctx.last_cmd_str()

    # --- repeat / history ---
    if text in ["again", "repeat", "that", "same"]:
        return last_cmd or user_input

    if "commands ago" in text:
        try:
            n = int(text.split()[0])
            return ctx.last_cmd_str(n) or user_input
        except Exception:
            pass

    # --- pronouns ---
    if "them" in text and ctx.entities.get("last_files"):
        return f"open {' '.join(ctx.entities['last_files'])}"
    if "it" in text and ctx.entities.get("last_process"):
        return f"kill {ctx.entities['last_process']}"
    if "there" in text and ctx.entities.get("last_dir"):
        return f"ls {ctx.entities['last_dir']}" if OS_NAME != "Windows" else f"dir {ctx.entities['last_dir']}"

    # --- synonyms for details ---
    if any(kw in text for kw in ["detailed", "in detail", "show details", "with details"]) and last_cmd:
        if OS_NAME in ["Linux", "Darwin"]:
            if "ls" in last_cmd:
                return last_cmd + " -la"
        elif OS_NAME == "Windows":
            if "dir" in last_cmd:
                return last_cmd + " /q /a"

    # --- synonyms for size sorting ---
    if any(kw in text for kw in ["by size", "sorted by size", "largest first", "order by size"]) and last_cmd:
        if OS_NAME in ["Linux", "Darwin"]:
            if "ls" in last_cmd:
                return last_cmd + " -lhS"
        elif OS_NAME == "Windows":
            if "dir" in last_cmd:
                return last_cmd + " /o:-s"

    # --- synonyms for navigation ---
    if any(kw in text for kw in ["now in", "go to", "move to", "switch to"]) and last_cmd:
        parts = text.split()
        if "in" in parts:
            idx = parts.index("in")
            if idx + 1 < len(parts):
                return f"{last_cmd} {parts[idx+1]}"
        if "to" in parts:  # handle "go to /path"
            idx = parts.index("to")
            if idx + 1 < len(parts):
                return f"{last_cmd} {parts[idx+1]}"

    # fallback: return unchanged
    return user_input
