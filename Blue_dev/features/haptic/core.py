# zomode/Blue_dev/features/haptic/core.py
import asyncio, os, json
from ...utils.logger import info, warn, error, good, dim
from ...utils.config_loader import load_feature_config, save_feature_config
async def _connect_and_write(address, char_uuid, payload: bytes):
    try:
        from bleak import BleakClient
    except Exception:
        raise RuntimeError('bleak not installed')
    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                raise RuntimeError('Could not connect')
            await client.write_gatt_char(char_uuid, payload)
            return True
    except Exception as e:
        raise

def send_pattern(address, pattern='short', char_uuid=None):
    cfg = load_feature_config('haptic') or {}
    char = char_uuid or cfg.get('char_uuid')
    if not char:
        warn('No characteristic configured for haptic device; cannot send pattern.')
        return False
    # Map pattern to payload (device-specific!). We'll use a simple convention.
    mapping = {
        'short': b'V:1',
        'pulse': b'V:2',
        'long': b'V:3'
    }
    pl = mapping.get(pattern, b'V:0')
    try:
        import asyncio
        return asyncio.run(_connect_and_write(address, char, pl))
    except Exception as e:
        error(f'Failed to send pattern: {e}')
        return False

def pair_device(name, address, char_uuid=None):
    cfg = load_feature_config('haptic') or {}
    devs = cfg.get('devices', {})
    devs[name] = {'address': address, 'char_uuid': char_uuid}
    cfg['devices'] = devs
    save_feature_config('haptic', cfg)
    good(f'Paired {name} -> {address} (char {char_uuid})')
    return True

def run_interactive():
    cfg = load_feature_config('haptic') or {}
    print('\nHaptic:\n1) Pair device manually\n2) Send test pattern\0) Back')
    while True:
        ch = input('Choose: ').strip()
        if ch == '0': break
        if ch == '1':
            name = input('Friendly name: ').strip()
            addr = input('Device address: ').strip()
            char = input('Write characteristic UUID (device specific): ').strip()
            pair_device(name, addr, char or None)
        elif ch == '2':
            name = input('Device name to test: ').strip()
            cfg = load_feature_config('haptic') or {}
            dev = cfg.get('devices', {}).get(name)
            if not dev:
                warn('Device not found')
                continue
            patt = input('Pattern (short/pulse/long): ').strip() or 'short'
            ok = send_pattern(dev['address'], patt, dev.get('char_uuid'))
            print('Sent:', ok)
        else:
            print('Invalid')

