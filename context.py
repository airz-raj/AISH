# context.py
"""
Context management for AISH
Keeps track of previous commands, results, and supports natural references
like "them", "those", "again", "2 commands ago".
"""

class AishContext:
    def __init__(self):
        self.history = []   # list of dicts: {command, result, type}

    def update(self, command, result, type_):
        self.history.append({
            "command": command,
            "result": result,
            "type": type_
        })

    def last_of_type(self, type_):
        for h in reversed(self.history):
            if h["type"] == type_:
                return h
        return None


# -----------------------------------------------------
# Context Resolution
# -----------------------------------------------------
def resolve_with_context(command: str, context: AishContext):
    lower = command.lower()
    history = context.history

    if not history:
        return command

    # Repeat last
    if lower in ["again", "repeat", "same"]:
        return history[-1]["command"]

    # Pronoun references
    for ref in ["them", "those", "it"]:
        if ref in lower:
            last = next((h for h in reversed(history) if h["type"]), None)
            if last:
                command = command.replace(ref, last["type"])

    # Explicit "N commands ago"
    import re
    match = re.search(r"(\d+)\s+commands?\s+ago", lower)
    if match:
        n = int(match.group(1))
        if len(history) >= n:
            old = history[-n]
            command = command.replace(match.group(0), old["type"] or "result")

    return command
