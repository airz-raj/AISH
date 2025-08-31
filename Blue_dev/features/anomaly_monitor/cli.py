# zomode/Blue_dev/features/anomaly_monitor/cli.py
from .core import run_interactive
def register_commands(subparsers):
    am = subparsers.add_parser('onist', help='Anomaly monitor and onist tools')
    sp = am.add_subparsers(dest='onist_cmd')
    mon = sp.add_parser('monitor', help='Start/stop monitor')
    mon.set_defaults(func=lambda args: run_interactive())
def run():
    run_interactive()
