# zomode/Blue_dev/features/ble_bridge/core.py
import asyncio, time, json, os
from ...utils.logger import info, warn, error, good, dim
from ...utils.config_loader import load_feature_config, save_feature_config

async def _discover(timeout=5.0):
    try:
        from bleak import BleakScanner
    except Exception as e:
        error('bleak library not available for BLE scanning. Install bleak.')
        return []
    try:
        devs = await BleakScanner.discover(timeout=timeout)
        results = [{'name': d.name or '<unknown>', 'address': d.address} for d in devs]
        return results
    except Exception as e:
        error(f'BLE scan failed: {e}')
        return []

def discover_devices(timeout=5.0):
    return asyncio.run(_discover(timeout))

def link_tag(name, address):
    cfg = load_feature_config('ble_bridge') or {}
    tags = cfg.get('ble_tags', {})
    tags[name] = address
    cfg['ble_tags'] = tags
    save_feature_config('ble_bridge', cfg)
    good(f'Linked tag {name} -> {address}')
    return True

def ping_tag(name, timeout=3.0):
    cfg = load_feature_config('ble_bridge') or {}
    addr = cfg.get('ble_tags', {}).get(name)
    if not addr:
        warn('Tag not linked')
        return False
    try:
        from bleak import BleakClient
    except Exception:
        error('bleak not installed')
        return False
    async def _ping(a):
        try:
            async with BleakClient(a) as client:
                return client.is_connected
        except Exception as e:
            error(f'Ping failed: {e}')
            return False
    return asyncio.run(_ping(addr))

def run_interactive():
    cfg = load_feature_config('ble_bridge') or {}
    while True:
        print('\nBLE Bridge:\n1) Discover\n2) Link by choosing discovered\n3) Ping linked\n0) Back')
        ch = input('Choose: ').strip()
        if ch == '0': break
        if ch == '1':
            devs = discover_devices(5.0)
            for i,d in enumerate(devs,1):
                print(f"{i}) {d['name']} {d['address']}")
        elif ch == '2':
            devs = discover_devices(5.0)
            for i,d in enumerate(devs,1):
                print(f"{i}) {d['name']} {d['address']}")
            sel = input('Choose number to link: ').strip()
            try:
                idx = int(sel)-1
                if 0<=idx<len(devs):
                    name = input('Friendly name: ').strip()
                    link_tag(name, devs[idx]['address'])
            except Exception as e:
                warn('Invalid selection')
        elif ch == '3':
            name = input('Tag name to ping: ').strip()
            ok = ping_tag(name)
            print('Ping connected:' , ok)
        else:
            print('Invalid')

