"""
NEXUS Security Worker — scans the network, monitors devices,
checks for threats, tracks the Xiaomi camera.
"""

import socket, threading, time, subprocess
from datetime import datetime


KNOWN_DEVICES = {
    '192.168.1.1':  {'name': 'Router',        'mac': '04:BF:6D:CC:FE:EA', 'threat': 'SAFE'},
    '192.168.1.34': {'name': 'Xiaomi Cam C',   'mac': '94:F8:27:82:20:B6', 'threat': 'NO TOKEN'},
    '192.168.1.47': {'name': 'This Device',    'mac': 'local',              'threat': 'SAFE'},
}


class SecurityWorker:
    def __init__(self):
        self.devices    = dict(KNOWN_DEVICES)
        self.scan_pct   = 0
        self.last_scan  = None
        self.threat_lvl = 'LOW'
        self.events     = []
        self._thread    = None
        self._stop      = threading.Event()
        self._lock      = threading.Lock()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _ping(self, ip):
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '0.3', ip],
                capture_output=True, timeout=1
            )
            return result.returncode == 0
        except:
            return False

    def _scan_subnet(self):
        """Quick scan of local /24 subnet."""
        self.scan_pct = 0
        active = {}
        base = '192.168.1.'
        threads = []

        found = {}
        lock = threading.Lock()

        def check(i):
            ip = base + str(i)
            if self._ping(ip):
                info = KNOWN_DEVICES.get(ip, {'name': f'Unknown-{i}', 'mac': '??:??:??:??:??:??', 'threat': 'UNKNOWN'})
                with lock:
                    found[ip] = info
            self.scan_pct = int(i / 254 * 100)

        for i in range(1, 30):  # quick scan first 30
            if self._stop.is_set():
                return
            t = threading.Thread(target=check, args=(i,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=2)

        with self._lock:
            self.devices = {**KNOWN_DEVICES, **found}
            self.last_scan = datetime.now().strftime('%H:%M:%S')
            self.scan_pct = 100

    def _check_camera(self):
        """Check if Xiaomi camera is reachable."""
        ip = '192.168.1.34'
        alive = self._ping(ip)
        with self._lock:
            if ip in self.devices:
                self.devices[ip]['alive'] = alive
                self.devices[ip]['last_seen'] = datetime.now().strftime('%H:%M:%S') if alive else 'timeout'

    def _loop(self):
        # Initial scan
        self._scan_subnet()
        self._log_event('Network scan complete')

        while not self._stop.is_set():
            time.sleep(30)
            self._check_camera()
            if not self._stop.is_set():
                time.sleep(30)
                self._scan_subnet()
                self._log_event('Periodic scan')

    def _log_event(self, msg):
        ts = datetime.now().strftime('%H:%M:%S')
        with self._lock:
            self.events.insert(0, f'{ts} {msg}')
            self.events = self.events[:20]

    def get_status(self):
        with self._lock:
            return {
                'devices':    dict(self.devices),
                'scan_pct':   self.scan_pct,
                'last_scan':  self.last_scan,
                'threat_lvl': self.threat_lvl,
                'events':     list(self.events[:5]),
            }
