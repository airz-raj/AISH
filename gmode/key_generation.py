# gmode/key_generation.py

import json
import os
import random
import string
import tempfile
import subprocess

def generate_random_key(length=32):
    """Generate a random alphanumeric key."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_key_flow(token: str = None):
    """
    Handles full key generation + PR flow.
    `token` is optional — if not provided, function will still run.
    """
    try:
        repo_url = "https://github.com/Karan-Paliwal/AISH-DATABASE.git"
        clone_dir = tempfile.mkdtemp()

        print("[*] Cloning repository...")
        subprocess.run(["git", "clone", repo_url, clone_dir], check=True)

        keys_file = os.path.join(clone_dir, "Keys.json")

        if os.path.exists(keys_file):
            with open(keys_file, "r") as f:
                data = json.load(f)
        else:
            data = {}

        # Generate new key
        new_key = generate_random_key()
        user = os.getenv("USER", "unknown_user")
        data[user] = new_key

        with open(keys_file, "w") as f:
            json.dump(data, f, indent=4)

        print(f"[*] New key generated for {user}: {new_key}")

        # Git operations
        subprocess.run(["git", "-C", clone_dir, "checkout", "-b", f"add-key-{user}"], check=True)
        subprocess.run(["git", "-C", clone_dir, "add", "Keys.json"], check=True)
        subprocess.run(["git", "-C", clone_dir, "commit", "-m", f"Add key for {user}"], check=True)
        subprocess.run(["git", "-C", clone_dir, "push", "origin", f"add-key-{user}"], check=True)

        print("[*] Pull request created — please visit GitHub to finalize.")
        print("    (Owner just needs to approve/merge PR)")

    except Exception as e:
        print(f"Unexpected error: {e}")
