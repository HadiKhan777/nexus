"""
NEXUS RAG Engine — indexes all of Hadi's documents and code into a
local vector store using TF-IDF. No external APIs. Runs entirely offline.
"""

import os, re, math, json, threading
from pathlib import Path
from collections import Counter


class Document:
    def __init__(self, path, content, source_type):
        self.path = path
        self.content = content
        self.source_type = source_type  # code, readme, cv, internship
        self.tokens = self._tokenize(content)

    def _tokenize(self, text):
        return re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]{2,}\b', text.lower())


class RAGEngine:
    def __init__(self, status_cb=None):
        self.docs = []
        self.idf = {}
        self.status_cb = status_cb or (lambda s: None)
        self._lock = threading.Lock()
        self.indexed = 0
        self.total = 0

    def _update(self, msg):
        self.status_cb(msg)

    def index_all(self):
        """Index everything — code, READMEs, CV, internship notes."""
        sources = [
            (Path.home() / 'neuralkit',  'code',      ['*.py']),
            (Path.home() / 'nanohttp',   'code',      ['*.js']),
            (Path.home() / 'gitlet',     'code',      ['*.js']),
            (Path.home() / 'distkv',     'code',      ['*.js']),
            (Path.home() / 'tui',        'code',      ['*.js']),
            (Path.home() / 'kontainer',  'code',      ['*.js']),
            (Path.home() / 'pipecraft',  'code',      ['*.js']),
            (Path.home() / 'neuralkit',  'readme',    ['*.md']),
            (Path.home() / 'nanohttp',   'readme',    ['*.md']),
            (Path.home() / 'gitlet',     'readme',    ['*.md']),
            (Path.home() / 'portfolio',  'readme',    ['*.md']),
            (Path.home() / 'Downloads',  'cv',        ['*CV*.docx', '*CV*.pdf']),
            (Path.home() / 'claude-wiki' / 'wiki', 'wiki', ['*.md']),
        ]

        paths = []
        for base, stype, patterns in sources:
            if base.exists():
                for pat in patterns:
                    paths.extend([(p, stype) for p in base.rglob(pat) if p.is_file() and p.stat().st_size < 200_000])

        self.total = len(paths)
        self._update(f'Indexing {self.total} documents...')

        new_docs = []
        for i, (p, stype) in enumerate(paths):
            try:
                if stype == 'cv' and p.suffix == '.docx':
                    continue  # skip binary
                text = p.read_text(errors='ignore')[:8000]
                if len(text.strip()) > 50:
                    new_docs.append(Document(str(p), text, stype))
            except:
                pass
            self.indexed = i + 1

        # Add hardcoded Hadi context
        hadi_context = """
Abdul Hadi Khan. Computer Engineering student at Kadir Has University Istanbul 2022-2026.
Built 7 projects from scratch with zero runtime dependencies:
distkv: distributed KV store TCP WAL replication 19312 ops/sec benchmark.
neuralkit: neural network NumPy only BatchNorm GELU AdamW cosine LR 99.4% accuracy.
nanohttp: HTTP1.1 WebSocket RFC6455 JWT HS256 SSE gzip zero dependencies.
gitlet: git from scratch SHA256 3-way merge stash tags LCS diff.
tui: terminal UI framework raw ANSI 30fps FocusManager ScrollList Tabs.
kontainer: container runtime Linux namespaces cgroup v2 no Docker no root.
pipecraft: CICD pipeline engine parallel jobs toposort retry artifacts webhook.
Internships: Stewart Pakistan 40 days NET Angular PowerPlatform Azure AI 15 certs.
InfoTech 20 days React Redux REST APIs.
Generix Solutions 20 days Rust Python CLI tools System Monitor Pro.
19 certifications including Azure AI-900 Power Platform GitHub Foundations NET Fundamentals.
Languages Python Rust JavaScript TypeScript Kotlin Java C C++ C#.
Xiaomi camera at 192.168.1.34 MAC 94F8278220B6 needs token for RTSP access.
Email hadikhan2003@gmail.com GitHub HadiKhan777.
"""
        new_docs.append(Document('internal://hadi-context', hadi_context, 'identity'))

        with self._lock:
            self.docs = new_docs
        self._build_idf()
        self._update(f'Indexed {len(self.docs)} documents. Ready.')

    def _build_idf(self):
        N = len(self.docs)
        df = Counter()
        for doc in self.docs:
            for term in set(doc.tokens):
                df[term] += 1
        self.idf = {t: math.log((N + 1) / (c + 1)) for t, c in df.items()}

    def _tfidf_score(self, query_tokens, doc):
        tf = Counter(doc.tokens)
        total = len(doc.tokens) or 1
        score = 0
        for t in query_tokens:
            if t in tf:
                score += (tf[t] / total) * self.idf.get(t, 0)
        return score

    def search(self, query, top_k=5):
        """Return top_k most relevant document snippets for the query."""
        with self._lock:
            if not self.docs:
                return []
        q_tokens = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]{2,}\b', query.lower())
        scored = [(self._tfidf_score(q_tokens, d), d) for d in self.docs]
        scored.sort(key=lambda x: -x[0])
        results = []
        for score, doc in scored[:top_k]:
            if score > 0:
                snippet = doc.content[:600].replace('\n', ' ').strip()
                results.append({
                    'path': doc.path,
                    'type': doc.source_type,
                    'score': round(score, 4),
                    'snippet': snippet
                })
        return results

    def build_context(self, query):
        """Build a context string from retrieved docs for LLM prompting."""
        results = self.search(query, top_k=4)
        if not results:
            return ''
        ctx = '\n\n'.join(
            f'[{r["type"].upper()} — {os.path.basename(r["path"])}]\n{r["snippet"]}'
            for r in results
        )
        return f'Relevant context from Hadi\'s knowledge base:\n{ctx}\n\n'
