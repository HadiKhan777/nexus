"""
NEXUS Obsidian Writer — agents write their findings directly into ~/claude-wiki.

When any agent completes a task, it creates/appends a node so all future
agents (and Claude sessions) can benefit from what was learned.
"""

import threading, re
from datetime import datetime
from pathlib import Path

WIKI = Path.home() / 'claude-wiki' / 'wiki'
AGENTS_DIR = WIKI / 'agents'


class ObsidianWriter:
    def __init__(self):
        self._lock = threading.Lock()
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    def log_finding(self, agent_name, provider_name, task, result):
        """Write an agent's finding as an Obsidian node."""
        slug = re.sub(r'[^a-z0-9]+', '-', agent_name.lower())
        path = AGENTS_DIR / f'{slug}.md'

        ts      = datetime.now().strftime('%Y-%m-%d %H:%M')
        entry   = (f'\n## {ts} — {provider_name}\n'
                   f'**Task:** {task[:120]}\n\n'
                   f'{result[:500]}\n')

        with self._lock:
            if path.exists():
                # Append — never overwrite
                with open(path, 'a') as f:
                    f.write(entry)
            else:
                header = (f'---\ntype: agent-log\nagent: {agent_name}\n'
                          f'provider: {provider_name}\ncreated: {ts}\n---\n\n'
                          f'# {agent_name} Agent Log\n\n'
                          f'Provider: [[{provider_name}]]\n'
                          f'Related: [[nexus-project]] · [[hadi-khan]]\n')
                path.write_text(header + entry)

    def write_insight(self, title, content, tags=None):
        """Write a new concept/insight node to the wiki."""
        slug  = re.sub(r'[^a-z0-9]+', '-', title.lower())[:50]
        path  = WIKI / 'concepts' / f'ai-insight-{slug}.md'
        tags  = tags or []
        ts    = datetime.now().strftime('%Y-%m-%d')

        if path.exists():
            with self._lock:
                with open(path, 'a') as f:
                    f.write(f'\n## Updated {ts}\n{content[:800]}\n')
        else:
            node = (f'---\ntype: concept\ntags: [{", ".join(tags)}]\n'
                    f'created: {ts}\nsource: nexus-agent\n---\n\n'
                    f'# {title}\n\n{content[:800]}\n\n'
                    f'## Related\n[[nexus-project]] · [[hadi-khan]]\n')
            with self._lock:
                path.write_text(node)

    def recent_agent_context(self, agent_name, n=3):
        """Read the last n findings from an agent's log for context."""
        slug = re.sub(r'[^a-z0-9]+', '-', agent_name.lower())
        path = AGENTS_DIR / f'{slug}.md'
        if not path.exists():
            return ''
        text = path.read_text()
        # Find last n ## sections
        sections = re.split(r'\n## ', text)
        recent   = sections[-n:] if len(sections) > n else sections[1:]
        if not recent:
            return ''
        return f'[{agent_name} recent findings from Obsidian]\n' + '\n---\n'.join(recent)
