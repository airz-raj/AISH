# zomode/Blue_dev/features/anomaly_monitor/core.py
import threading, time, os, json, datetime
from ...utils.logger import info, warn, error, good, dim
from ...utils.config_loader import load_feature_config, save_feature_config

class AnomalyMonitor:
    def __init__(self, config=None):
        self.config = config or load_feature_config('anomaly_monitor') or {}
        self._stop = threading.Event()
        self._thread = None
        self.logfile = os.path.join(os.path.dirname(__file__), 'logs.jsonl')
        self.previous_remote_ports = {}  # track ports per remote IP
        self.known_remotes = set()
        self.last_io = None  # for outbound bytes
        self.threshold_bytes = self.config.get('rules', {}).get('excessive_outbound_bytes', 10485760)

    def _log(self, etype, meta):
        entry = {'time': datetime.datetime.utcnow().isoformat()+'Z', 'type': etype, 'meta': meta}
        try:
            with open(self.logfile, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            error(f'Write log failed: {e}')

    def _check_psutil(self):
        try:
            import psutil
        except Exception:
            return
        # foreign ip detection & port scan heuristics via psutil connections
        try:
            conns = psutil.net_connections(kind='inet')
            # map remote ip -> set of remote ports seen this interval
            temp = {}
            for c in conns:
                r = c.raddr
                if not r:
                    continue
                rip = r.ip
                port = r.port
                temp.setdefault(rip, set()).add(port)
                if rip not in self.known_remotes:
                    self.known_remotes.add(rip)
                    self._log('new_remote', {'ip': rip, 'port': port})
                # detect many different ports from same remote -> possible scan
                prev = self.previous_remote_ports.get(rip, set())
                combined = prev.union(temp[rip])
                if len(combined) - len(prev) > 20:
                    self._log('port_scan_suspected', {'ip': rip, 'unique_ports': len(combined)})
            self.previous_remote_ports = temp
        except Exception as e:
            # psutil may not be available or permissions insufficient
            pass
        # check outbound bytes via net_io_counters
        try:
            io = psutil.net_io_counters()
            now = time.time()
            if self.last_io:
                last_time, last_bytes = self.last_io
                delta_bytes = io.bytes_sent - last_bytes
                delta_t = now - last_time
                if delta_bytes > self.threshold_bytes:
                    self._log('excessive_outbound', {'bytes_sent': delta_bytes, 'duration_s': delta_t})
            self.last_io = (now, io.bytes_sent)
        except Exception:
            pass

    def _scapy_sniff(self):
        # attempt to use scapy for deeper packet inspection (only if available)
        try:
            from scapy.all import sniff, IP, TCP
        except Exception:
            return
        def _proc(pkt):
            try:
                if IP in pkt and TCP in pkt:
                    sip = pkt[IP].src
                    dip = pkt[IP].dst
                    sport = pkt[TCP].sport
                    dport = pkt[TCP].dport
                    # crude detection: many SYNs from remote -> potential scan
                    # We do light-weight handling to avoid heavy computation
                    self._log('packet', {'src': sip, 'dst': dip, 'sport': sport, 'dport': dport})
            except Exception:
                pass
        try:
            sniff(prn=_proc, timeout=5, store=0)
        except Exception:
            pass

    def _loop(self):
        info('Anomaly monitor loop started')
        while not self._stop.is_set():
            # prefer psutil heuristics (safer cross-platform)
            self._check_psutil()
            # attempt a small scapy sniff if available
            self._scapy_sniff()
            time.sleep(2)
        info('Anomaly monitor loop exiting')

    def start(self):
        if self._thread and self._thread.is_alive():
            warn('Monitor already running')
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        good('Anomaly monitor started')

    def stop(self):
        if not self._thread:
            warn('Monitor not running')
            return
        self._stop.set()
        self._thread.join(timeout=2.0)
        good('Anomaly monitor stopped')

    def show_logs(self):
        try:
            with open(self.logfile, 'r') as f:
                print(f.read())
        except Exception as e:
            warn('No logs available')

# interactive runner
_mon = None
def run_interactive():
    global _mon
    if _mon is None:
        _mon = AnomalyMonitor()
    print('\nAnomaly Monitor: start / stop / showlog / back')
    while True:
        cmd = input('> ').strip().lower()
        if cmd in ('back','b','exit','quit'):
            break
        if cmd == 'start':
            _mon.start()
        elif cmd == 'stop':
            _mon.stop()
        elif cmd == 'showlog':
            _mon.show_logs()
        else:
            print('Unknown. Valid: start stop showlog back')

