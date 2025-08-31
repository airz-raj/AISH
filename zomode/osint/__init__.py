from . import tools
from .tools import osint_menu as tools_menu

def osint_menu(args=None):
    """
    Unified ONIST menu for OSINT:
    - JSON plugins (interactive)
    - .py/.sh/.bat scripts from scripts/ folder
    - Pull/Push/Run functionality
    """
    tools_menu()  # calls the fully-featured tools.py menu
