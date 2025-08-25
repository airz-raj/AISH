# autocomplete.py
"""
Advanced autocomplete with VS Code-like faded suggestions
"""

import os
from typing import List, Dict, Any

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import ANSI, FormattedText
    from prompt_toolkit.styles import Style
    from prompt_toolkit.document import Document
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

class AISHCompleter(Completer):
    """Custom completer for AISH with better matching"""
    
    def __init__(self, commands: Dict[str, Any], patterns: Dict[str, Any], builtins: List[str]):
        self.commands = commands
        self.patterns = patterns
        self.builtins = builtins
        self.all_words = set(builtins)
        self.all_words.update(commands.keys())
        self.all_words.update(patterns.keys())
        self.all_words.update(['help', 'menu', 'history', 'clear', 'exit'])
    
    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor.lower()
        
        # Get matching words with priority
        matches = []
        for word in self.all_words:
            if word.lower().startswith(text.lower()):
                matches.append((word, 10))  # High priority for prefix matches
            elif text.lower() in word.lower():
                matches.append((word, 5))   # Medium priority for contains matches
        
        # Sort by priority then alphabetically
        matches.sort(key=lambda x: (-x[1], x[0]))
        
        for word, _ in matches:
            # Calculate display text with faded unmatched part
            if text and len(word) > len(text):
                matched_part = word[:len(text)]
                unmatched_part = word[len(text):]
                display_text = FormattedText([
                    ('#ffffff', matched_part),  # White for matched part
                    ('#888888', unmatched_part)  # Gray for unmatched part
                ])
            else:
                display_text = word
            
            yield Completion(
                word,
                start_position=-len(text),
                display=display_text,
                style='bg:#004444 #ffffff'
            )

def create_advanced_autocompleter(commands_json, patterns_json, core_commands):
    """Create advanced autocompleter instance"""
    if not HAS_PROMPT_TOOLKIT:
        return None
    
    builtins = list(core_commands.COMMAND_REGISTRY.keys())
    return AISHCompleter(commands_json, patterns_json, builtins)

def get_advanced_input(prompt_text, completer):
    """Get input with advanced autocomplete"""
    if not HAS_PROMPT_TOOLKIT or not completer:
        return input(prompt_text)
    
    try:
        style = Style.from_dict({
            'completion-menu.completion': 'bg:#004444 #ffffff',
            'completion-menu.completion.current': 'bg:#008888 #000000',
            'scrollbar.background': 'bg:#88aaaa',
            'scrollbar.button': 'bg:#222222',
        })
        
        session = PromptSession(completer=completer, style=style)
        return session.prompt(ANSI(prompt_text))
    except Exception:
        return input(prompt_text)