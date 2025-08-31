# zomode/Blue_dev/__init__.py
import json, os, importlib
from colorama import Fore, Style, init as _init
_init(autoreset=True)
from .feature_loader import load_feature_module, list_feature_entries
from .utils.logger import info, warn, good, error


def blue_dev_menu():
    base_path = os.path.dirname(__file__)
    cfg_path = os.path.join(base_path, 'blue_features.json')
    if not os.path.exists(cfg_path):
        warn('[Blue-dev] blue_features.json missing')
        return
    try:
        with open(cfg_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        error(f'[Blue-dev] failed to read blue_features.json: {e}')
        return
    features = data.get('features', [])

    while True:
        print(f"\n{Fore.LIGHTRED_EX}=== Blue-dev — Hardware & Guardian Lab ==={Style.RESET_ALL}")
        for i, fe in enumerate(features, 1):
            name = fe.get('name') or fe.get('module')
            enabled = fe.get('enabled', True)
            flag = Fore.GREEN + '[ON]' if enabled else Fore.YELLOW + '[OFF]'
            print(f"{Fore.LIGHTRED_EX}{i}) {Fore.LIGHTWHITE_EX}{name} {Style.RESET_ALL}{flag}")
        print(f"{Fore.LIGHTRED_EX}0) {Fore.LIGHTWHITE_EX}Back{Style.RESET_ALL}")

        choice = input(Fore.LIGHTCYAN_EX + 'Select an option: ' + Style.RESET_ALL).strip()
        if choice in ('0','b','back','q','quit','exit'):
            break
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(features):
                warn('Invalid choice')
                continue
            feat = features[idx]
            if not feat.get('enabled', True):
                warn('Feature is disabled. Toggle it in blue_features.json.')
                continue
            mod = load_feature_module(feat.get('module'))
            if mod is None:
                warn(f"Feature module '{feat.get('module')}' not available.")
                continue
            # prefer interactive entry points
            if hasattr(mod, 'run') and callable(mod.run):
                mod.run()
            elif hasattr(mod, 'menu') and callable(mod.menu):
                mod.menu()
            else:
                info('Feature has no run/menu entry point; attempting to call cli.register_commands if available.')
                try:
                    cli = importlib.import_module(f"Blue_dev.features.{feat.get('module')}.cli")
                    if hasattr(cli, 'run'):
                        cli.run()
                    else:
                        warn('No runnable entry found for feature.')
                except Exception as e:
                    error(f'Failed to run feature cli: {e}')
        except ValueError:
            warn('Please enter a number')
