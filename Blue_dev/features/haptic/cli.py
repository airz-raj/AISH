# zomode/Blue_dev/features/haptic/cli.py
from .core import send_pattern, pair_device, run_interactive
def register_commands(subparsers):
    h = subparsers.add_parser('haptic', help='Haptic utilities')
    h.add_argument('action', nargs='?', default='status')
def run():
    run_interactive()
