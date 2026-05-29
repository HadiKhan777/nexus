"""
NEXUS Web Search — real HTTP search via DuckDuckGo (no API key needed).
Used by the ORACLE and RESEARCHER agents.
"""

import requests, re, html, urllib.parse


def search(query, max_results=5):
    """DuckDuckGo instant answer + HTML scrape. No API key."""
    results = []

    # DuckDuckGo instant answers API
    try:
        r = requests.get(
            'https://api.duckduckgo.com/',
            params={'q': query, 'format': 'json', 'no_redirect': 1, 'no_html': 1},
            timeout=6, headers={'User-Agent': 'NEXUS/1.0'}
        )
        data = r.json()
        if data.get('AbstractText'):
            results.append({
                'title':   data.get('Heading', 'DuckDuckGo'),
                'snippet': data['AbstractText'][:300],
                'url':     data.get('AbstractURL', ''),
                'source':  'instant',
            })
        for r2 in data.get('RelatedTopics', [])[:3]:
            if isinstance(r2, dict) and r2.get('Text'):
                results.append({
                    'title':   r2.get('Text', '')[:60],
                    'snippet': r2.get('Text', '')[:200],
                    'url':     r2.get('FirstURL', ''),
                    'source':  'related',
                })
    except:
        pass

    # Fallback: scrape DuckDuckGo HTML
    if not results:
        try:
            r = requests.get(
                f'https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}',
                timeout=6,
                headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
            )
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
            titles   = re.findall(r'<a class="result__a"[^>]*>(.*?)</a>', r.text, re.DOTALL)
            for i, (t, s) in enumerate(zip(titles[:max_results], snippets[:max_results])):
                results.append({
                    'title':   html.unescape(re.sub(r'<[^>]+>', '', t)).strip()[:80],
                    'snippet': html.unescape(re.sub(r'<[^>]+>', '', s)).strip()[:250],
                    'url':     '',
                    'source':  'web',
                })
        except:
            pass

    return results[:max_results]


def format_for_llm(query, results):
    if not results:
        return f'Web search for "{query}" returned no results.'
    lines = [f'Web search results for: {query}\n']
    for i, r in enumerate(results, 1):
        lines.append(f'{i}. {r["title"]}')
        lines.append(f'   {r["snippet"]}')
    return '\n'.join(lines)
