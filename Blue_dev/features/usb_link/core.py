# zomode/Blue_dev/features/usb_link/core.py
import threading, time, os
from ...utils.logger import info, warn, error, good, dim
from ...utils.config_loader import load_feature_config, save_feature_config
import subprocess

class USBListener:
    def __init__(self, vid=None, pid=None, serial_port=None, mapping=None):
        self.vid = vid
        self.pid = pid
        self.serial_port = serial_port
        self.mapping = mapping or (load_feature_config('usb_link') or {}).get('usb_mappings', {}).get('events', {})
        self.led_map = (load_feature_config('usb_link') or {}).get('usb_mappings', {}).get('led_feedback', {})
        self._stop = threading.Event()
        self._thread = None
        self.dev = None
        self._use_serial = False

    def open_device(self):
        # Try pyusb HID first, fallback to pyserial
        try:
            import usb.core, usb.util
            usb_present = True
        except Exception:
            usb_present = False
        try:
            import serial
            serial_present = True
        except Exception:
            serial_present = False

        if self.serial_port and serial_present:
            info(f'Opening serial port {self.serial_port} as CDC fallback')
            self.dev = ('serial', self.serial_port)
            self._use_serial = True
            return True

        if self.vid and self.pid and usb_present:
            try:
                vid = int(self.vid, 16) if isinstance(self.vid, str) else self.vid
                pid = int(self.pid, 16) if isinstance(self.pid, str) else self.pid
                dev = usb.core.find(idVendor=vid, idProduct=pid)
                if dev is None:
                    warn('USB device with provided VID:PID not found')
                    return False
                # detach kernel driver if needed (Linux)
                try:
                    if dev.is_kernel_driver_active(0):
                        dev.detach_kernel_driver(0)
                except Exception:
                    pass
                dev.set_configuration()
                self.dev = ('hid', dev)
                info('Opened HID device (pyusb)')
                return True
            except Exception as e:
                warn(f'pyusb open failed: {e}')
        warn('No suitable device opened (pyusb/pyserial missing or device not found)')
        return False

    def close(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self.dev and self.dev[0] == 'hid':
            try:
                import usb.util
                usb.util.dispose_resources(self.dev[1])
            except Exception:
                pass
        info('USB listener closed')

    def _send_led(self, state):
        color = self.led_map.get(state)
        if not color:
            return
        # For HID: write to OUT endpoint if available; For serial: write text
        if not self.dev:
            return
        try:
            if self.dev[0] == 'serial':
                import serial
                ser = serial.Serial(self.dev[1], baudrate=115200, timeout=0.2)
                ser.write(f"LED:{color}\n".encode())
                ser.close()
            else:
                # HID: best-effort using control transfer (vendor-specific devices may require custom)
                d = self.dev[1]
                try:
                    d.ctrl_transfer(0x40, 0x01, 0, 0, bytes(f"LED:{color}\n", 'utf-8'))
                except Exception:
                    # ignore if not supported
                    pass
        except Exception as e:
            warn(f'Failed to set LED: {e}')

    def _execute_mapped(self, cmd):
        info(f'Executing mapped command: {cmd}')
        try:
            # Show running feedback
            self._send_led('running')
            # run the command as subprocess (allow shell-style)
            proc = subprocess.run(cmd, shell=True)
            if proc.returncode == 0:
                self._send_led('success')
            else:
                self._send_led('failure')
        except Exception as e:
            warn(f'Command execution failed: {e}')
            self._send_led('failure')

    def _read_loop(self):
        info('USB listener loop started (polling)')
        while not self._stop.is_set():
            try:
                # If serial mode, read a line
                if self.dev and self.dev[0] == 'serial':
                    import serial, time
                    try:
                        ser = serial.Serial(self.dev[1], baudrate=115200, timeout=0.3)
                        line = ser.readline().decode(errors='ignore').strip()
                        ser.close()
                        if line:
                            token = line.strip()
                            info(f'Read token: {token}')
                            cmd = self.mapping.get(token)
                            if cmd:
                                threading.Thread(target=self._execute_mapped, args=(cmd,), daemon=True).start()
                    except Exception as e:
                        # transient serial read errors ignored
                        pass
                elif self.dev and self.dev[0] == 'hid':
                    # For HID, poll interrupt IN endpoint if possible
                    d = self.dev[1]
                    try:
                        cfg = d.get_active_configuration()
                        intf = cfg[(0,0)]
                        in_ep = None
                        for ep in intf.endpoints():
                            if ep.bEndpointAddress & 0x80:
                                in_ep = ep
                                break
                        if in_ep:
                            try:
                                data = in_ep.read(in_ep.wMaxPacketSize, timeout=200)
                                if data:
                                    token = bytes(data).strip(b"\x00").decode(errors='ignore').strip()
                                    if token:
                                        info(f'Read HID token: {token}')
                                        cmd = self.mapping.get(token)
                                        if cmd:
                                            threading.Thread(target=self._execute_mapped, args=(cmd,), daemon=True).start()
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    # no device; sleep
                    time.sleep(0.5)
            except Exception as e:
                warn(f'Listener loop error: {e}')
                time.sleep(0.5)
        info('USB listener loop exiting')

    def start(self, background=False):
        ok = self.open_device()
        if not ok:
            warn('Device open failed; aborting listener')
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        good('USB listener started')
        if not background:
            try:
                while self._thread.is_alive():
                    time.sleep(0.2)
            except KeyboardInterrupt:
                self.close()
        return True

# public helpers
def start_listener(vendor_id=None, product_id=None, serial_port=None):
    lst = USBListener(vendor_id, product_id, serial_port)
    return lst.start(background=False)

def test_led(state='running'):
    cfg = load_feature_config('usb_link')
    led_map = cfg.get('usb_mappings', {}).get('led_feedback', {})
    print('LED mapping:', led_map)
    # Attempt to send to serial port if provided in config
    port = cfg.get('serial_port')
    if port:
        try:
            import serial
            ser = serial.Serial(port, baudrate=115200, timeout=0.5)
            color = led_map.get(state, 'off')
            ser.write(f"LED:{color}\n".encode())
            ser.close()
            print('Sent LED command via serial')
        except Exception as e:
            print('Failed to send serial LED:', e)
    else:
        print('No serial port configured for test.')
