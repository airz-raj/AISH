# zomode/Blue_dev/features/ble_bridge/cli.py
from .core import discover_devices, link_tag, ping_tag, run_interactive
def register_commands(subparsers):
    ble = subparsers.add_parser('tag', help='BLE tag utilities')
    sp = ble.add_subparsers(dest='tag_cmd')
    link = sp.add_parser('link', help='Link a BLE tag')
    link.set_defaults(func=lambda args: run_interactive())
    scan = sp.add_parser('scan', help='Scan for BLE devices')
    scan.set_defaults(func=lambda args: print(discover_devices()))
def run():
    run_interactive()
