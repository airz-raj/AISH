# core_commands.py
"""
Core builtin commands used by AISH.
Each function accepts a single argument: args (list of strings) and prints output.
COMMAND_REGISTRY maps command key -> function.
"""

import os
import sys
import json
import socket
import zipfile
import re
import platform
from datetime import datetime
from typing import List, Optional

try:
    import psutil
except Exception:
    psutil = None  # optional but recommended

from utils import run_subprocess, detect_os

# -------------------------
# Helpers
# -------------------------
def _safe_read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None

# -------------------------
# System info
# -------------------------
def sysinfo(args: List[str] = None):
    """sysinfo — show system info (OS, CPU, RAM, uptime, IP)"""
    uname = platform.uname()
    print(f"System: {uname.system} {uname.release} ({uname.version})")
    print(f"Node: {uname.node}")
    print(f"Machine: {uname.machine}")
    print(f"Processor: {uname.processor or 'N/A'}")
    print(f"CPU cores: {os.cpu_count() or 1}")
    if psutil:
        mem = psutil.virtual_memory()
        print(f"Memory: {mem.total // (1024**2)} MB total, {mem.available // (1024**2)} MB available")
        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot
        print("Uptime:", str(uptime).split('.')[0])
    else:
        print("Memory: (install psutil for more detail)")

    # local IP
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"Local IP: {local_ip}")
    except Exception:
        print("Local IP: N/A")

def battery(args: List[str] = None):
    """battery — show battery percentage (if available)"""
    if not psutil:
        print("psutil not installed — battery information unavailable.")
        return
    try:
        bat = psutil.sensors_battery()
        if not bat:
            print("No battery detected.")
            return
        status = "Charging" if bat.power_plugged else "Discharging"
        print(f"Battery: {bat.percent}% — {status}")
    except Exception as e:
        print("Error reading battery info:", e)

# -------------------------
# File tools
# -------------------------
def zip_cmd(args: List[str]):
    """zip <out.zip> <folder>"""
    if not args or len(args) < 2:
        print("Usage: zip <out.zip> <folder>")
        return
    outzip = args[0]
    folder = args[1]
    if not os.path.exists(folder):
        print("Folder not found:", folder)
        return
    try:
        with zipfile.ZipFile(outzip, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(folder):
                for f in files:
                    path = os.path.join(root, f)
                    arcname = os.path.relpath(path, start=folder)
                    z.write(path, arcname)
        print(f"Zipped {folder} → {outzip}")
    except Exception as e:
        print("Zip failed:", e)

def unzip_cmd(args: List[str]):
    """unzip <file.zip> <dest>"""
    if not args or len(args) < 2:
        print("Usage: unzip <file.zip> <dest>")
        return
    zfile = args[0]
    dest = args[1]
    if not os.path.exists(zfile):
        print("Zip file not found:", zfile)
        return
    try:
        with zipfile.ZipFile(zfile, 'r') as z:
            z.extractall(dest)
        print(f"Extracted {zfile} → {dest}")
    except Exception as e:
        print("Unzip failed:", e)

def search_cmd(args: List[str]):
    """search <text> <folder> — search for text inside files"""
    if not args or len(args) < 2:
        print("Usage: search <text> <folder>")
        return
    needle = args[0]
    folder = args[1]
    matches = []
    for root, _, files in os.walk(folder):
        for fname in files:
            path = os.path.join(root, fname)
            try:
                with open(path, 'r', errors='ignore') as fh:
                    content = fh.read()
                if needle in content:
                    print(path)
            except Exception:
                continue

def renamebulk_cmd(args: List[str]):
    """renamebulk <pattern> <replacement> [folder]"""
    if not args or len(args) < 2:
        print("Usage: renamebulk <pattern> <replacement> [folder]")
        return
    pattern = args[0]
    repl = args[1]
    folder = args[2] if len(args) >= 3 else "."
    try:
        compiled = re.compile(pattern)
    except Exception as e:
        print("Invalid regex pattern:", e)
        return
    changed = 0
    for fname in os.listdir(folder):
        new_name = compiled.sub(repl, fname)
        if new_name != fname:
            os.rename(os.path.join(folder, fname), os.path.join(folder, new_name))
            changed += 1
    print(f"Renamed {changed} files in {folder}")

# -------------------------
# Network tools
# -------------------------
def ping_cmd(args: List[str]):
    """ping <host>"""
    if not args:
        print("Usage: ping <host>")
        return
    host = args[0]
    system = detect_os()
    cmd = f"ping -n 4 {host}" if system == "windows" else f"ping -c 4 {host}"
    code, out, err = run_subprocess(cmd)
    if out:
        print(out.strip())
    if err:
        print(err.strip())

def traceroute_cmd(args: List[str]):
    """traceroute <host>"""
    if not args:
        print("Usage: traceroute <host>")
        return
    host = args[0]
    system = detect_os()
    cmd = f"tracert {host}" if system == "windows" else f"traceroute {host}"
    code, out, err = run_subprocess(cmd)
    if out:
        print(out.strip())
    if err:
        print(err.strip())

def scanport_cmd(args: List[str]):
    """scanport <host> <port>"""
    if not args or len(args) < 2:
        print("Usage: scanport <host> <port>")
        return
    host = args[0]
    try:
        port = int(args[1])
    except Exception:
        print("Invalid port")
        return
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        result = s.connect_ex((host, port))
        if result == 0:
            print(f"Port {port} on {host} is OPEN")
        else:
            print(f"Port {port} on {host} is CLOSED")
    except Exception as e:
        print("Error:", e)
    finally:
        s.close()

# -------------------------
# Process tools
# -------------------------
def ps_cmd(args: List[str]):
    """ps — list processes (requires psutil)"""
    if not psutil:
        print("psutil not installed — process listing not available.")
        return
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        try:
            info = proc.info
            print(f"{info.get('pid'):>6}  {info.get('username','')[:15]:15}  {info.get('name')}")
        except Exception:
            continue

def kill_cmd(args: List[str]):
    """kill <pid> — terminate a process (requires psutil)"""
    if not args:
        print("Usage: kill <pid>")
        return
    if not psutil:
        print("psutil required to kill processes safely.")
        return
    try:
        pid = int(args[0])
        p = psutil.Process(pid)
        p.terminate()
        print(f"Terminated {pid}")
    except Exception as e:
        print("Error terminating:", e)

# -------------------------
# Text utilities
# -------------------------
def wc_cmd(args: List[str]):
    """wc <file> — line/word/char count"""
    if not args:
        print("Usage: wc <file>")
        return
    fname = args[0]
    if not os.path.exists(fname):
        print("File not found:", fname)
        return
    try:
        with open(fname, 'r', errors='ignore') as f:
            data = f.read()
        lines = data.count("\n") + (1 if data else 0)
        words = len(data.split())
        chars = len(data)
        print(f"Lines: {lines}  Words: {words}  Chars: {chars}")
    except Exception as e:
        print("Error reading file:", e)

def formatjson_cmd(args: List[str]):
    """formatjson <file> — pretty-print JSON"""
    if not args:
        print("Usage: formatjson <file>")
        return
    fname = args[0]
    if not os.path.exists(fname):
        print("File not found:", fname)
        return
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(json.dumps(data, indent=4, ensure_ascii=False))
    except Exception as e:
        print("Invalid JSON or error:", e)

# -------------------------
# Registry
# -------------------------
COMMAND_REGISTRY = {
    "sysinfo": sysinfo,
    "battery": battery,
    "zip": zip_cmd,
    "unzip": unzip_cmd,
    "search": search_cmd,
    "renamebulk": renamebulk_cmd,
    "ping": ping_cmd,
    "traceroute": traceroute_cmd,
    "scanport": scanport_cmd,
    "ps": ps_cmd,
    "kill": kill_cmd,
    "wc": wc_cmd,
    "formatjson": formatjson_cmd
}
