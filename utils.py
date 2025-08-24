# utils.py
import sys
import os
import subprocess
import platform
from typing import Tuple

def resource_path(relative_path: str) -> str:
    """
    Returns path to resource, works when running as script and when packaged by PyInstaller.
    If running as onefile exe (PyInstaller), resources bundled with --add-data are extracted to sys._MEIPASS.
    """
    try:
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def detect_os() -> str:
    return platform.system().lower()

def run_subprocess(cmd: str, cwd: str = None, capture_output: bool = True) -> Tuple[int, str, str]:
    """
    Run a shell command and return (returncode, stdout, stderr).
    capture_output True returns captured output; otherwise returns ("","") for stdout/stderr but still runs.
    """
    try:
        proc = subprocess.run(cmd, shell=True, text=True, capture_output=capture_output, cwd=cwd)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except Exception as e:
        return 1, "", str(e)
