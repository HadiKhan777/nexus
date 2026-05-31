"""
NEXUS Obsidian Chat Logger — every conversation is stored as a
dated session note in ~/claude-wiki/wiki/sessions/.

The RAG engine already indexes ~/claude-wiki, so tomorrow's NEXUS
session automatically has context from today's conversations.
This creates a self-reinforcing knowledge loop:
  conversation → Obsidian node → RAG index → richer context
"""

import threading, re
from datetime import datetime
from pathlib import Path

WIKI_SESSIONS = Path.home() / 'claude-wiki' / 'wiki' / 'sessions'


class ObsidianChatLogger:
    def __init__(self):
        self._lock = threading.Lock()
        WIKI_SESSIONS.mkdir(parents=True, exist_ok=True)
        self._today_file = None
        self._ensure_file()

    def _ensure_file(self):
        date = datetime.now().strftime('%Y-%m-%d')
        path = WIKI_SESSIONS / f'nexus-chat-{date}.md'
        if not path.exists():
            path.write_text(
                f'---\ntype: session\ntags: [nexus, chat, ai]\n'
                f'created: {datetime.now().isoformat()}\n---\n\n'
                f'# NEXUS Chat — {date}\n\n'
                f'Auto-logged by NEXUS. Indexed by RAG for future context.\n\n'
            )
        self._today_file = path

    def log(self, role, text):
        """Append a message to today's session note."""
        self._ensure_file()
        ts     = datetime.now().strftime('%H:%M')
        prefix = '**You**' if role == 'user' else '**NEXUS**'
        # Clean text — strip ANSI if any leaked through
        clean = re.sub(r'\x1b\[[0-9;]*m', '', text).strip()
        if not clean:
            return
        entry = f'\n### {ts}\n{prefix}: {clean}\n'
        with self._lock:
            with open(self._today_file, 'a') as f:
                f.write(entry)

    def log_insight(self, topic, content):
        """Write a standalone insight node — used for important facts."""
        date  = datetime.now().strftime('%Y-%m-%d')
        slug  = re.sub(r'[^a-z0-9]+', '-', topic.lower())[:40]
        path  = Path.home() / 'claude-wiki' / 'wiki' / 'concepts' / f'nexus-insight-{slug}-{date}.md'
        if not path.exists():
            node = (f'---\ntype: concept\ntags: [nexus, insight]\n'
                    f'created: {date}\n---\n\n'
                    f'# {topic}\n\n{content}\n\n'
                    f'## Source\n[[nexus-project]] · auto-generated\n')
            with self._lock:
                path.write_text(node)
