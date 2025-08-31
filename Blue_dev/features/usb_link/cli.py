# zomode/Blue_dev/features/usb_link/cli.py
from .core import start_listener, test_led
from ...utils.logger import info, warn, good, error
from ...utils.config_loader import load_feature_config, save_feature_config
import os

def register_commands(subparsers):
    hw = subparsers.add_parser('hardware', help='USB hardware link')
    sp = hw.add_subparsers(dest='hw_cmd')
    listen = sp.add_parser('listen', help='Start USB listener')
    listen.add_argument('--device', nargs=2, help='VID PID in hex')
    listen.add_argument('--serial-port', help='Serial port (CDC fallback)')
    listen.set_defaults(func=lambda args: run_from_args(args))
    t = sp.add_parser('test-led', help='Test LED')
    t.add_argument('--state', default='running')
    t.set_defaults(func=lambda args: test_led(args.state))

def run_from_args(args):
    vid = None; pid = None; spath = None
    if getattr(args, 'device', None):
        vid, pid = args.device[0], args.device[1]
    if getattr(args, 'serial_port', None):
        spath = args.serial_port
    start_listener(vid, pid, spath)

def run():
    print('--- USB Link ---')
    cfg = load_feature_config('usb_link')
    while True:
        print('\n1) Start listener\n2) Test LED mapping\n0) Back')
        ch = input('Choose: ').strip()
        if ch == '0': break
        if ch == '1':
            dev = input('Enter VID (hex, e.g. 0x2341) or blank to use config: ').strip()
            if not dev:
                vid = cfg.get('vendor_id')
                pid = cfg.get('product_id')
            else:
                vid = dev; pid = input('Enter PID (hex): ').strip()
            sp = input('Serial port (optional, e.g. /dev/ttyACM0 or COM3): ').strip() or None
            start_listener(vid, pid, sp)
        elif ch == '2':
            st = input('State to test (running/success/failure): ').strip() or 'running'
            test_led(st)
        else:
            print('Invalid')

