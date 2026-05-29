"""
NEXUS File Watcher — monitors all 7 repos for live changes.
Shows what's being worked on in real-time.
"""

import os, time, threading, hashlib
from pathlib import Path
from datetime import datetime


class FileWatcher:
    def __init__(self):
        self.events   = []   # recent change events
        self.watching = []   # paths being watched
        self._hashes  = {}
        self._lock    = threading.Lock()
        self._thread  = None
        self._stop    = threading.Event()

        # Watch all repos
        repos = ['neuralkit','nanohttp','gitlet','tui','kontainer','pipecraft','distkv','nexus']
        for repo in repos:
            p = Path.home() / repo
            if p.exists():
                self.watching.append(p)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _hash_file(self, path):
        try:
            return hashlib.md5(Path(path).read_bytes()).hexdigest()[:8]
        except:
            return None

    def _scan(self):
        exts = {'.py','.js','.ts','.rs','.md','.json','.html','.css'}
        for repo_path in self.watching:
            for f in repo_path.rglob('*'):
                if f.suffix not in exts: continue
                if '__pycache__' in str(f) or 'node_modules' in str(f): continue
                if not f.is_file(): continue
                key = str(f)
                h   = self._hash_file(f)
                if h is None: continue
                prev = self._hashes.get(key)
                if prev is not None and prev != h:
                    rel  = f.relative_to(Path.home())
                    evt  = {
                        'path':   str(rel),
                        'repo':   rel.parts[0],
                        'file':   f.name,
                        'ext':    f.suffix,
                        'time':   datetime.now().strftime('%H:%M:%S'),
                        'size':   f.stat().st_size,
                    }
                    with self._lock:
                        self.events.insert(0, evt)
                        self.events = self.events[:30]
                self._hashes[key] = h

    def _loop(self):
        self._scan()  # baseline
        while not self._stop.is_set():
            time.sleep(2)
            if not self._stop.is_set():
                self._scan()

    def recent(self, n=8):
        with self._lock:
            return list(self.events[:n])
