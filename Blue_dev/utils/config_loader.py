# zomode/Blue_dev/utils/config_loader.py
import os, json
BASE = os.path.dirname(os.path.dirname(__file__))  # features parent
FEATURES_DIR = os.path.join(BASE, 'features')
def get_feature_config_path(feature_name):
    return os.path.join(FEATURES_DIR, feature_name, 'config.json')
def load_feature_config(feature_name):
    path = get_feature_config_path(feature_name)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}
def save_feature_config(feature_name, data):
    path = get_feature_config_path(feature_name)
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
            return True
    except Exception:
        return False

def get_master_features_path():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_dir, "blue_features.json")
