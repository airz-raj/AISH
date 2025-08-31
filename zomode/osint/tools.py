import os
import sys
import json
import shutil
import subprocess
import platform
import time
import traceback
from colorama import init, Fore, Style

# Initialize colorama

init(autoreset=True)

# ----------------- Directories -----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_SCRIPTS_DIR = "custom_scripts"
SCRIPTS_DIR = "scripts"
PLUGIN_FILE = os.path.join(BASE_DIR, "osint_plugins.json")
ALLOWED_EXT = {".py", ".sh", ".bat"}

PLUGINS = []

# ----------------- Terminal helpers -----------------
def typewriter(text, delay=0.01, color=Fore.LIGHTWHITE_EX):
    for ch in text:
        sys.stdout.write(f"{color}{ch}")
        sys.stdout.flush()
        time.sleep(delay)
    print()

def print_colored_menu(options):
    for idx, opt in enumerate(options, 1):
        print(f"{Fore.LIGHTRED_EX}{idx}) {Fore.LIGHTWHITE_EX}{opt}")
    print(f"{Fore.LIGHTRED_EX}0) {Fore.LIGHTWHITE_EX}Back")

# ----------------- Plugin handling -----------------
def load_plugins():
    global PLUGINS
    PLUGINS = []
    if os.path.exists(PLUGIN_FILE):
        try:
            data = json.load(open(PLUGIN_FILE, "r"))
            if isinstance(data, list):
                for idx, plugin in enumerate(data, 1):
                    if "name" in plugin and ("file" in plugin or "code" in plugin):
                        PLUGINS.append(plugin)
                    else:
                        print(f"⚠ Skipping invalid plugin entry #{idx}")
            else:
                print("⚠ Plugin JSON is not a list")
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")

def create_json_plugin():
    typewriter("Enter plugin name: ", color=Fore.LIGHTCYAN_EX)
    name = input().strip()
    typewriter("Enter plugin description: ", color=Fore.LIGHTCYAN_EX)
    desc = input().strip()
    typewriter("Enter plugin code (define run()). Type END to finish:", color=Fore.LIGHTCYAN_EX)
    code_lines = []
    while True:
        line = input(">>> ")
        if line.strip().upper() == "END":
            break
        code_lines.append(line)
    code = "\n".join(code_lines)
    PLUGINS.append({"name": name, "description": desc, "code": code})
    try:
        with open(PLUGIN_FILE, "w") as f:
            json.dump(PLUGINS, f, indent=2)
        typewriter(f"✅ Plugin '{name}' saved.", color=Fore.GREEN)
    except Exception as e:
        typewriter(f"❌ Failed to save plugin: {e}", color=Fore.LIGHTRED_EX)

def run_json_plugin(plugin):
    try:
        local_env = {}
        exec(plugin["code"], {}, local_env)
        if "run" in local_env:
            try:
                local_env["run"]()
            except Exception as e:
                typewriter(f"❌ Error in plugin execution: {e}", color=Fore.LIGHTRED_EX)
                traceback.print_exc()
        else:
            typewriter("❌ Plugin missing run()", color=Fore.LIGHTRED_EX)
    except Exception as e:
        typewriter(f"❌ Failed to run plugin '{plugin.get('name','?')}': {e}", color=Fore.LIGHTRED_EX)
        traceback.print_exc()

# ----------------- Script execution -----------------
def install_requirements(script_path):
    req_file = os.path.join(os.path.dirname(script_path), "requirements.txt")
    if os.path.exists(req_file):
        typewriter(f"📦 Installing requirements for {os.path.basename(script_path)}...", color=Fore.YELLOW)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
            typewriter("✅ Requirements installed", color=Fore.GREEN)
        except subprocess.CalledProcessError as e:
            typewriter(f"❌ Failed to install requirements: {e}", color=Fore.LIGHTRED_EX)

def run_script_file(script_path):
    name = os.path.basename(script_path)
    system = platform.system()
    try:
        if name.endswith(".py"):
            install_requirements(script_path)
            subprocess.run([sys.executable, script_path])
        elif name.endswith((".sh", ".zsh")):
            if system in ["Linux", "Darwin"]:
                subprocess.run(["bash", script_path])
            else:
                typewriter(f"❌ Cannot run {name}: .sh/.zsh only on Linux/macOS", color=Fore.LIGHTRED_EX)
        elif name.endswith(".bat"):
            if system == "Windows":
                subprocess.run([script_path], shell=True)
            else:
                typewriter(f"❌ Cannot run {name}: .bat only on Windows", color=Fore.LIGHTRED_EX)
        else:
            typewriter(f"⚠ Unknown script type: {name}", color=Fore.YELLOW)
    except Exception as e:
        typewriter(f"❌ Failed to run script {name}: {e}", color=Fore.LIGHTRED_EX)
        traceback.print_exc()

# ----------------- Delete script/plugin -----------------
def delete_script():
    global PLUGINS
    deletable_plugins = [p for p in PLUGINS if "file" in p and p["file"].startswith(CUSTOM_SCRIPTS_DIR + os.sep)]
    if not deletable_plugins:
        typewriter("⚠ No deletable scripts available.", color=Fore.YELLOW)
        return

    typewriter("\nSelect a script to delete:", color=Fore.LIGHTRED_EX)
    for i, plugin in enumerate(deletable_plugins, 1):
        print(f"{Fore.LIGHTRED_EX}{i}) {Fore.LIGHTWHITE_EX}{plugin['name']} ({plugin.get('type','')})")
    print(f"{Fore.LIGHTRED_EX}0) {Fore.LIGHTWHITE_EX}Back")

    sel = input(Fore.LIGHTCYAN_EX + "Enter choice: " + Style.RESET_ALL).strip()
    if sel == "0":
        return
    try:
        idx = int(sel) - 1
        if 0 <= idx < len(deletable_plugins):
            plugin = deletable_plugins[idx]
            script_path = os.path.join(BASE_DIR, plugin["file"])
            if os.path.exists(script_path):
                os.remove(script_path)
                typewriter(f"✅ File '{plugin['file']}' removed from folder.", color=Fore.GREEN)
            else:
                typewriter(f"⚠ File '{plugin['file']}' does not exist.", color=Fore.YELLOW)
            PLUGINS = [p for p in PLUGINS if p != plugin]
            with open(PLUGIN_FILE, "w") as f:
                json.dump(PLUGINS, f, indent=2)
            typewriter(f"✅ Plugin '{plugin['name']}' removed from JSON registry.", color=Fore.GREEN)
        else:
            typewriter("❌ Invalid choice", color=Fore.LIGHTRED_EX)
    except ValueError:
        typewriter("❌ Please enter a number", color=Fore.LIGHTRED_EX)

# ----------------- Push scripts to JSON -----------------
def push_scripts_to_json():
    global PLUGINS
    existing_files = {p["file"] for p in PLUGINS if "file" in p}
    new_scripts = []

    for folder, is_primary in [(SCRIPTS_DIR, True), (CUSTOM_SCRIPTS_DIR, False)]:
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.exists(folder_path):
            continue
        for filename in os.listdir(folder_path):
            name, ext = os.path.splitext(filename)
            rel_path = os.path.join(folder, filename).replace("\\", "/")
            if ext.lower() in ALLOWED_EXT and rel_path not in existing_files:
                new_entry = {
                    "name": name,
                    "file": rel_path,
                    "type": ext.lower()[1:],
                    "primary": is_primary
                }
                PLUGINS.append(new_entry)
                new_scripts.append(filename)
                existing_files.add(rel_path)

    # <--- Save updated PLUGINS to JSON
    if new_scripts:
        with open(PLUGIN_FILE, "w") as f:
            json.dump(PLUGINS, f, indent=2)
        typewriter(f"✅ Pushed scripts to JSON: {', '.join(new_scripts)}", color=Fore.GREEN)




# ----------------- Import script -----------------
def import_script(primary=False):
    typewriter("Enter full path of the script to import: ", color=Fore.LIGHTCYAN_EX)
    path = input().strip()
    if not os.path.isfile(path):
        typewriter("❌ Invalid path or file does not exist.", color=Fore.LIGHTRED_EX)
        return
    name, ext = os.path.splitext(os.path.basename(path))
    if ext.lower() not in ALLOWED_EXT:
        typewriter("❌ Only .py, .sh, or .bat scripts are allowed.", color=Fore.LIGHTRED_EX)
        return
    target_dir = SCRIPTS_DIR if not primary else CUSTOM_SCRIPTS_DIR
    target_path = os.path.join(BASE_DIR, target_dir)
    os.makedirs(target_path, exist_ok=True)
    dest_path = os.path.join(target_path, os.path.basename(path))
    if os.path.exists(dest_path):
        typewriter(f"⚠ {os.path.basename(path)} already exists.", color=Fore.YELLOW)
    else:
        shutil.copy2(path, dest_path)
        typewriter(f"✅ Script copied to folder: {os.path.join(target_dir, os.path.basename(path))}", color=Fore.GREEN)
    rel_path = os.path.join(target_dir, os.path.basename(path)).replace("\\", "/")
    new_entry = {
        "name": name,
        "file": rel_path,
        "type": ext.lower()[1:],
        "primary": primary
    }
    PLUGINS.append(new_entry)
    with open(PLUGIN_FILE, "w") as f:
        json.dump(PLUGINS, f, indent=2)
    typewriter(f"✅ Script '{name}' added to JSON registry.", color=Fore.GREEN)

# ----------------- Loading animation -----------------
def loading_dots(message="Loading", duration=1.0):
    dots = ["   ", ".  ", ".. ", "..."]
    end_time = time.time() + duration
    idx = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r{Fore.LIGHTGREEN_EX}{message}{dots[idx % len(dots)]}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.6)
        idx += 1
    print("\r", end="")

def startup_animation():
    typewriter("Initializing OSINT Toolkit...", color=Fore.LIGHTCYAN_EX)
    loading_dots("Starting", duration=1.0)

# ----------------- OSINT Menu -----------------
def osint_menu():
    startup_animation()
    load_plugins()
    push_scripts_to_json()
    system = platform.system()

    while True:
        typewriter("\n=== OSINT Toolkit ===", color=Fore.LIGHTRED_EX)
        options = ["Run a Script", "New JSON Plugin", "Import Script from Path", "Delete Script/Plugin"]
        print_colored_menu(options)
        choice = input(Fore.LIGHTCYAN_EX + "Select an option: " + Style.RESET_ALL).strip()
        if choice == "0":
            break
        elif choice == "1":
            system = platform.system()
            file_plugins = [
                p for p in PLUGINS
                if "file" in p and (
                    p["file"].endswith(".py") or
                    (p["file"].endswith(".bat") and system == "Windows") or
                    (p["file"].endswith((".sh", ".zsh")) and system in ["Linux", "Darwin"])
                )
            ]
            if not file_plugins:
                typewriter("⚠ No scripts found for this OS.", color=Fore.YELLOW)
                continue
            typewriter("\nSelect a script to run:", color=Fore.LIGHTRED_EX)
            for i, plugin in enumerate(file_plugins, 1):
                plugin_type = plugin.get("type", plugin["file"].split('.')[-1])
                print(f"{Fore.LIGHTRED_EX}{i}) {Fore.LIGHTWHITE_EX}{plugin['name']} ({plugin_type})")
            print(f"{Fore.LIGHTRED_EX}0) {Fore.LIGHTWHITE_EX}Back")
            sel = input(Fore.LIGHTCYAN_EX + "Enter choice: " + Style.RESET_ALL).strip()
            if sel == "0":
                continue
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(file_plugins):
                    plugin = file_plugins[idx]
                    loading_dots(f"Executing {plugin['name']}", duration=1.0)
                    script_path = os.path.join(BASE_DIR, plugin["file"])
                    if not os.path.exists(script_path):
                        typewriter(f"❌ Script file not found: {plugin['file']}", color=Fore.LIGHTRED_EX)
                        continue
                    run_script_file(script_path)
                else:
                    typewriter("❌ Invalid choice", color=Fore.LIGHTRED_EX)
            except ValueError:
                typewriter("❌ Please enter a number", color=Fore.LIGHTRED_EX)
        elif choice == "2":
            create_json_plugin()
            load_plugins()
        elif choice == "3":
            import_script()
            load_plugins()
        elif choice == "4":
            delete_script()
            load_plugins()
        else:
            typewriter("❌ Invalid option", color=Fore.LIGHTRED_EX)

if __name__ == "__main__":
    osint_menu()
