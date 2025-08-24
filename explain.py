import json

def explain_command(cmd):
    with open("explain.json") as f:
        explanations = json.load(f)
    parts = cmd.split()
    return " | ".join([f"{p}: {explanations.get(p, 'Unknown')}" for p in parts])
