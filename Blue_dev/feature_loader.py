import importlib
import json
import os
from types import ModuleType
from .utils.config_loader import get_master_features_path

BASE = os.path.dirname(__file__)
FEATURES_DIR = os.path.join(BASE, "features")

_cache = {}

def _blue_features_path():
    return os.path.join(BASE, "blue_features.json")

# Blue_dev/feature_loader.py

def list_enabled_features():
    path = _blue_features_path()
    try:
        with open(path, "r") as f:
            data = json.load(f)
        # Newer schema: {"features": [{"module": "...", "enabled": true}, ...]}
        if "features" in data and isinstance(data["features"], list):
            return [
                fe.get("module")
                for fe in data["features"]
                if fe and fe.get("enabled", True) and fe.get("module")
            ]
        # Legacy schema: {"enabled_features": ["usb_link", ...]}
        return data.get("enabled_features", [])
    except Exception:
        return []

def get_all_feature_names():
    """Inspect features directory and return all available features."""
    try:
        return [
            name
            for name in os.listdir(FEATURES_DIR)
            if os.path.isdir(os.path.join(FEATURES_DIR, name))
        ]
    except Exception:
        return []

def load_feature_module(name):
    """Wrapper: load a single feature by name"""
    modules = load_feature_modules()
    return modules.get(name)

def list_feature_entries():
    """Wrapper: return all available feature names"""
    return get_all_feature_names()

def load_feature_modules(full=False, reload_only=False):
    """Load and return dict name -> module for enabled features.
    If full=True returns list of all available features names.
    """
    if full:
        return get_all_feature_names()

    enabled = list_enabled_features()
    loaded = {}
    for fname in enabled:
        try:
            # ✅ FIXED: import from correct package
            mod_path = f"Blue_dev.features.{fname}.core"
            if reload_only and fname in _cache:
                importlib.reload(_cache[fname])
                loaded[fname] = _cache[fname]
            else:
                mod = importlib.import_module(mod_path)
                _cache[fname] = mod
                loaded[fname] = mod
        except Exception as e:
            # Fail soft
            print(f"[Blue_dev] failed to import {fname}: {e}")
    return loaded

def toggle_feature(name):
    """Enable/disable a feature by updating blue_features.json."""
    path = _blue_features_path()
    data = {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        data = {"enabled_features": []}

    lst = data.get("enabled_features", [])
    if name in lst:
        lst.remove(name)
    else:
        lst.append(name)
    data["enabled_features"] = lst

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[Blue_dev] updated enabled_features: {lst}")
