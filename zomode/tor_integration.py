# zomode/tor_integration.py
"""
Cross-platform Tor integration for AISH
- Feature detection
- Graceful fallbacks
- Platform-specific optimizations
"""

import os
import platform
import shutil
import subprocess
import glob

# Windows-only import guard
try:
    import winreg
except ImportError:
    winreg = None

# -------------------------
# Natural language → command mapping
# -------------------------
TOR_COMMAND_PATTERNS = {
    "route through tor": "torify",
    "run through tor network": "torify",
    "start tor browser": "tor-browser",
    "open anonymous browser": "tor-browser",
    "check tor status": "tor-status",
    "install tor": "tor-install",
    "enable tor": "tor-start",
    "disable tor": "tor-stop",
    "proxychains": "proxychains",
    "run with proxychains": "proxychains",
    "system-wide tor": "anonsurf-start",
    "enable anonsurf": "anonsurf-start",
    "disable anonsurf": "anonsurf-stop"
}

# -------------------------
# Auto-detection of Tor Browser path (cross-platform)
# -------------------------
def find_tor_browser_path():
    sysname = platform.system().lower()

    if "linux" in sysname:
        candidates = [
            os.path.expanduser("~/tor-browser_en-US/Browser/start-tor-browser"),
            os.path.expanduser("~/tor-browser*/Browser/start-tor-browser"),
            "/snap/bin/torbrowser-launcher",
            "/usr/bin/torbrowser-launcher",
            "/usr/local/bin/torbrowser-launcher",
        ]
        expanded = []
        for c in candidates:
            expanded.extend(glob.glob(c))
        candidates = expanded

    elif "darwin" in sysname:  # macOS
        candidates = [
            "/Applications/Tor Browser.app/Contents/MacOS/firefox",
            os.path.expanduser("~/Applications/Tor Browser.app/Contents/MacOS/firefox"),
        ]

    elif "windows" in sysname:
        candidates = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tor Browser\\Browser\\firefox.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Tor Browser\\Browser\\firefox.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Tor Browser\\Browser\\firefox.exe"),
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop\\Tor Browser\\Browser\\firefox.exe"),
            os.path.join(os.environ.get("ONEDRIVE", ""), "Desktop\\Tor Browser\\Browser\\firefox.exe"),
        ]

        # Registry uninstall entries (if available)
        if winreg:
            reg_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ]
            for reg_root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for reg_path in reg_paths:
                    try:
                        with winreg.OpenKey(reg_root, reg_path) as key:
                            for i in range(winreg.QueryInfoKey(key)[0]):
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                        if "Tor Browser" in display_name:
                                            install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                            exe_path = os.path.join(install_loc, "Browser\\firefox.exe")
                                            candidates.append(exe_path)
                                    except FileNotFoundError:
                                        pass
                    except FileNotFoundError:
                        pass
    else:
        return None

    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

# -------------------------
# Platform-specific mappings
# -------------------------
def _linux_tor_impl():
    return {
        "torify": "torify",
        "system_wide": "anonsurf",      # system-wide tor routing
        "proxychains": "proxychains4",  # or proxychains (package dependent)
        "browser": find_tor_browser_path(),
        "check_cmd": "systemctl is-active tor"
    }

def _macos_tor_impl():
    return {
        "torify": "torsocks",
        "system_wide": None,  # anonsurf isn’t common on macOS
        "proxychains": "proxychains",  # brew install proxychains-ng
        "browser": find_tor_browser_path(),
        "check_cmd": "brew services list | grep tor"
    }

def _windows_tor_impl():
    return {
        "torify": None,
        "system_wide": None,
        "browser": find_tor_browser_path(),
        "check_cmd": 'tasklist | findstr "tor.exe"'
    }

# -------------------------
# Utility functions
# -------------------------
def detect_platform():
    sysname = platform.system().lower()
    if "linux" in sysname:
        return "linux"
    elif "darwin" in sysname:
        return "darwin"
    elif "windows" in sysname:
        return "windows"
    return sysname

def check_command_exists(cmd):
    return shutil.which(cmd) is not None

def run_subprocess(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        return {
            "code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except Exception as e:
        return {"code": 1, "stdout": "", "stderr": str(e)}

# -------------------------
# Safety check
# -------------------------
def tor_safety_check(cmd):
    """Prevent dangerous commands over Tor."""
    dangerous_patterns = ["sudo", "rm -rf", "dd if=", "mkfs", "> /dev/sda"]
    for pattern in dangerous_patterns:
        if pattern in cmd:
            return False, f"Dangerous command detected: {pattern}"
    return True, "Safe to run through Tor"

# -------------------------
# Tor Manager
# -------------------------
class TorManager:
    def __init__(self):
        self.platform = detect_platform()
        self.impl = self._get_platform_impl()
        self.available = self._check_availability()
    
    def _get_platform_impl(self):
        if self.platform == "linux":
            return _linux_tor_impl()
        elif self.platform == "darwin":
            return _macos_tor_impl()
        elif self.platform == "windows":
            return _windows_tor_impl()
        return {}
    
    def _check_availability(self):
        available_features = {
            "torify": False,
            "system_wide": False,
            "browser": False,
            "tor_running": False
        }
        if self.impl.get("torify"):
            available_features["torify"] = check_command_exists(self.impl["torify"])
        if self.impl.get("system_wide"):
            available_features["system_wide"] = check_command_exists(self.impl["system_wide"])
        if self.impl.get("browser"):
            available_features["browser"] = os.path.exists(os.path.expanduser(self.impl["browser"]))
        if self.impl.get("check_cmd"):
            result = run_subprocess(self.impl["check_cmd"])
            available_features["tor_running"] = (result["code"] == 0 and "inactive" not in result["stdout"].lower())
        return available_features

# -------------------------
# Command functions
# -------------------------
def tor_proxychains_cmd(args):
    """proxychains <command> - Run command through ProxyChains (Linux/macOS)."""
    if not tor_manager.impl.get("proxychains"):
        return "ProxyChains not available on this platform."
    if not check_command_exists(tor_manager.impl["proxychains"]):
        return "ProxyChains not installed. Install proxychains or proxychains-ng."
    if not args:
        return "Usage: proxychains <command>"
    cmd = f"{tor_manager.impl['proxychains']} {' '.join(args)}"
    result = run_subprocess(cmd)
    return result["stdout"] or result["stderr"]

def tor_anonsurf_start_cmd(args):
    """anonsurf-start - Start system-wide Tor (Linux only)."""
    if tor_manager.platform != "linux" or not check_command_exists("anonsurf"):
        return "Anonsurf not available on this platform."
    result = run_subprocess("sudo anonsurf start")
    return result["stdout"] or result["stderr"]

def tor_anonsurf_stop_cmd(args):
    """anonsurf-stop - Stop system-wide Tor (Linux only)."""
    if tor_manager.platform != "linux" or not check_command_exists("anonsurf"):
        return "Anonsurf not available on this platform."
    result = run_subprocess("sudo anonsurf stop")
    return result["stdout"] or result["stderr"]

def torify_cmd(args):
    """torify <command> - Run command through Tor."""
    if tor_manager.platform == "windows":
        if not args:
            return "Usage: torify <command>"
        # On Windows, just run the command as-is, expecting user to add --socks5 127.0.0.1:9150
        result = run_subprocess(" ".join(args))
        return result["stdout"] or result["stderr"]

    # Linux / macOS path
    if not tor_manager.available.get("torify"):
        return "Torify not available on this platform. Install torsocks/torify."
    if not args:
        return "Usage: torify <command>"
    safe, msg = tor_safety_check(" ".join(args))
    if not safe:
        return msg
    cmd = f"{tor_manager.impl['torify']} {' '.join(args)}"
    result = run_subprocess(cmd)
    return result["stdout"] or result["stderr"]


def tor_browser_cmd(args):
    """tor-browser - Launch Tor Browser."""
    if not tor_manager.available.get("browser"):
        return "Tor Browser not found. Please install it first."
    browser_path = tor_manager.impl["browser"]
    result = run_subprocess(f'"{browser_path}" {" ".join(args)}')
    return result["stdout"] or result["stderr"]

def tor_status_cmd(args):
    """tor-status - Check Tor connection status."""
    status = tor_manager.available
    if not any(status.values()):
        return "No Tor capabilities detected on this system."
    report = []
    if status["tor_running"]:
        report.append("✓ Tor service is running")
    else:
        report.append("✗ Tor service not running")
    if status["torify"]:
        report.append("✓ Command-level Tor available (torify/torsocks)")
    if status["system_wide"]:
        report.append("✓ System-wide Tor available (Anonsurf)")
    if status["browser"]:
        report.append("✓ Tor Browser available")
    return "\n".join(report)

def tor_install_cmd(args):
    """tor-install - Show installation instructions for current platform."""
    instructions = {
        "linux": """
# Linux (Debian/Ubuntu)
sudo apt update
sudo apt install tor torsocks

# Fedora
sudo dnf install tor torsocks

# Arch
sudo pacman -S tor torsocks

# (Optional) For Anonsurf:
git clone https://github.com/Und3rf10w/kali-anonsurf.git
cd kali-anonsurf
sudo ./installer.sh
""",
        "darwin": """
# macOS

# Install Homebrew if not installed:
 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then install Tor and torsocks:
 brew install tor torsocks

# Tor Browser (GUI):
Download from https://www.torproject.org/download/
""",
        "windows": """
# Windows

1. Download Tor Browser from the official website:
   https://www.torproject.org/download/

2. (Optional for developers) Download Tor Expert Bundle:
   https://www.torproject.org/download/tor/

3. Install and run Tor Browser, or extract the Expert Bundle and add tor.exe to PATH if you want command-line use.
"""
    }
    return instructions.get(detect_platform(), "Platform not supported for Tor installation guidance")

def tor_start_cmd(args):
    """tor-start - Start Tor service (Linux/macOS only)."""
    if tor_manager.platform == "linux":
        result = run_subprocess("sudo systemctl start tor")
        return result["stdout"] or result["stderr"]
    elif tor_manager.platform == "darwin":
        result = run_subprocess("brew services start tor")
        return result["stdout"] or result["stderr"]
    return "Tor service management not supported on Windows."

def tor_stop_cmd(args):
    """tor-stop - Stop Tor service (Linux/macOS only)."""
    if tor_manager.platform == "linux":
        result = run_subprocess("sudo systemctl stop tor")
        return result["stdout"] or result["stderr"]
    elif tor_manager.platform == "darwin":
        result = run_subprocess("brew services stop tor")
        return result["stdout"] or result["stderr"]
    return "Tor service management not supported on Windows."

# -------------------------
# Global instance
# -------------------------
tor_manager = TorManager()
