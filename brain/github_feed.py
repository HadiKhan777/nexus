"""
NEXUS GitHub Feed — live activity stream from HadiKhan777.
Polls for new commits, stars, and repo updates.
"""

import threading, time, requests
from datetime import datetime


class GitHubFeed:
    def __init__(self, username='HadiKhan777'):
        self.username = username
        self.events   = []
        self.repos    = []
        self.stars    = 0
        self.last_update = None
        self._thread  = None
        self._stop    = threading.Event()
        self._lock    = threading.Lock()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _fetch(self):
        headers = {'Accept': 'application/vnd.github.v3+json'}
        base    = 'https://api.github.com'

        # Repos
        try:
            r = requests.get(f'{base}/users/{self.username}/repos?per_page=8&sort=updated',
                             headers=headers, timeout=5)
            if r.status_code == 200:
                repos = r.json()
                total_stars = sum(repo.get('stargazers_count', 0) for repo in repos)
                events = []
                for repo in repos[:8]:
                    pushed = repo.get('pushed_at', '')
                    if pushed:
                        dt = datetime.fromisoformat(pushed.replace('Z', '+00:00'))
                        delta = datetime.now().astimezone() - dt
                        secs  = delta.total_seconds()
                        if secs < 3600:
                            age = f'{int(secs//60)}m ago'
                        elif secs < 86400:
                            age = f'{int(secs//3600)}h ago'
                        else:
                            age = f'{int(secs//86400)}d ago'
                        events.append({
                            'repo': repo['name'],
                            'age':  age,
                            'lang': repo.get('language') or '—',
                            'desc': (repo.get('description') or '')[:40],
                            'stars': repo.get('stargazers_count', 0),
                        })
                with self._lock:
                    self.repos   = repos
                    self.events  = events
                    self.stars   = total_stars
                    self.last_update = datetime.now().strftime('%H:%M:%S')
        except:
            pass

    def _loop(self):
        self._fetch()
        while not self._stop.is_set():
            time.sleep(120)   # poll every 2 minutes (respect rate limits)
            if not self._stop.is_set():
                self._fetch()

    def get_feed(self):
        with self._lock:
            return list(self.events), self.stars, self.last_update
