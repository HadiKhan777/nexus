"""
NEXUS Persistent Memory — NEXUS remembers across restarts.

Stores:
  - conversation history (rolling, capped)
  - learned facts (things the user told NEXUS to remember)
  - command history (for up-arrow recall)
  - run statistics (boots, total messages, uptime)

Backed by plain JSON at ~/.nexus/memory.json. Thread-safe, atomic writes.
No external dependencies.
"""

import os, json, time, threading, tempfile
from datetime import datetime
from pathlib import Path


MEM_DIR  = Path.home() / '.nexus'
MEM_FILE = MEM_DIR / 'memory.json'

DEFAULT = {
    'version':      1,
    'created':      None,
    'boots':        0,
    'total_msgs':   0,
    'conversation': [],   # [{role, text, ts}]
    'facts':        [],   # [{text, ts}]
    'commands':     [],   # raw command strings, newest last
    'last_seen':    None,
}

MAX_CONVO    = 200
MAX_COMMANDS = 100
MAX_FACTS    = 500


class Memory:
    def __init__(self):
        self._lock = threading.Lock()
        MEM_DIR.mkdir(parents=True, exist_ok=True)
        self.data  = self._load()
        # Register this boot
        with self._lock:
            if not self.data.get('created'):
                self.data['created'] = datetime.now().isoformat()
            self.data['boots']     = self.data.get('boots', 0) + 1
            self.data['last_seen'] = datetime.now().isoformat()
        self._save()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load(self):
        if MEM_FILE.exists():
            try:
                data = json.loads(MEM_FILE.read_text())
                # Merge with defaults so new keys appear
                merged = dict(DEFAULT)
                merged.update(data)
                return merged
            except Exception:
                pass
        return dict(DEFAULT)

    def _save(self):
        """Atomic write — never corrupts on crash mid-write."""
        try:
            tmp = tempfile.NamedTemporaryFile(
                mode='w', dir=str(MEM_DIR), suffix='.tmp', delete=False)
            json.dump(self.data, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, MEM_FILE)
        except Exception:
            pass

    # ── Conversation ────────────────────────────────────────────────────────

    def add_message(self, role, text):
        with self._lock:
            self.data['conversation'].append({
                'role': role, 'text': text[:2000],
                'ts': datetime.now().isoformat(),
            })
            self.data['conversation'] = self.data['conversation'][-MAX_CONVO:]
            self.data['total_msgs'] = self.data.get('total_msgs', 0) + 1
        self._save()

    def recent_conversation(self, n=6):
        with self._lock:
            return [(m['role'], m['text']) for m in self.data['conversation'][-n:]]

    # ── Facts (long-term learned knowledge) ─────────────────────────────────

    def remember(self, fact):
        with self._lock:
            self.data['facts'].append({
                'text': fact.strip(),
                'ts': datetime.now().isoformat(),
            })
            self.data['facts'] = self.data['facts'][-MAX_FACTS:]
        self._save()

    def facts(self):
        with self._lock:
            return [f['text'] for f in self.data['facts']]

    def forget_all_facts(self):
        with self._lock:
            self.data['facts'] = []
        self._save()

    def facts_context(self):
        """Facts formatted for injection into the LLM prompt."""
        fs = self.facts()
        if not fs:
            return ''
        lines = '\n'.join(f'- {f}' for f in fs[-20:])
        return f'Things NEXUS has been told to remember:\n{lines}\n\n'

    # ── Command history ─────────────────────────────────────────────────────

    def add_command(self, cmd):
        cmd = cmd.strip()
        if not cmd:
            return
        with self._lock:
            # Dedupe consecutive identical commands
            if self.data['commands'] and self.data['commands'][-1] == cmd:
                return
            self.data['commands'].append(cmd)
            self.data['commands'] = self.data['commands'][-MAX_COMMANDS:]
        self._save()

    def command_history(self):
        with self._lock:
            return list(self.data['commands'])

    # ── Stats ────────────────────────────────────────────────────────────────

    def stats(self):
        with self._lock:
            created = self.data.get('created')
            age_days = 0
            if created:
                try:
                    delta = datetime.now() - datetime.fromisoformat(created)
                    age_days = delta.days
                except Exception:
                    pass
            return {
                'boots':      self.data.get('boots', 0),
                'total_msgs': self.data.get('total_msgs', 0),
                'facts':      len(self.data.get('facts', [])),
                'age_days':   age_days,
                'created':    created,
            }
