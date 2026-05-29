"""
NEXUS Voice — text-to-speech using espeak (zero dependencies).
Async queue so voice never blocks the UI.
"""

import subprocess, threading, queue, re, os


class VoiceEngine:
    def __init__(self, enabled=True, speed=170, pitch=50, voice='en'):
        self.enabled = enabled and self._check_espeak()
        self.speed   = speed
        self.pitch   = pitch
        self.voice   = voice
        self._q      = queue.Queue()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _check_espeak(self):
        try:
            subprocess.run(['which','espeak'], capture_output=True, check=True)
            return True
        except:
            return False

    def speak(self, text):
        if not self.enabled:
            return
        # Strip ANSI and trim
        clean = re.sub(r'\x1b\[[0-9;]*m', '', text)
        clean = re.sub(r'\[.*?\]', '', clean)  # strip markdown brackets
        clean = clean.strip()[:400]
        if clean:
            self._q.put_nowait(clean)

    def _loop(self):
        while True:
            text = self._q.get()
            try:
                subprocess.run(
                    ['espeak', '-s', str(self.speed), '-p', str(self.pitch),
                     '-v', self.voice, text],
                    capture_output=True, timeout=15
                )
            except:
                pass

    def stop(self):
        self.enabled = False
        try:
            subprocess.run(['pkill', 'espeak'], capture_output=True)
        except:
            pass
