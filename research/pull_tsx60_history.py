"""Save Wikipedia's S&P/TSX 60 article as it stood at several past dates (constituent tables)."""
import json, os, requests
os.makedirs('research/tsx60', exist_ok=True)
api = 'https://en.wikipedia.org/w/api.php'
hdr = {'User-Agent': 'tsx-value-check research (github actions)'}
for title in ['S&P/TSX 60', 'S&P/TSX Composite Index']:
    for ts in ['2014-01-15', '2015-01-15', '2016-01-15', '2017-01-15', '2018-01-15', '2019-01-15', '2020-01-15',
               '2021-01-15', '2022-01-15', '2023-01-15', '2024-01-15', '2025-01-15', '2026-01-15']:
        r = requests.get(api, headers=hdr, timeout=30, params={
            'action': 'query', 'prop': 'revisions', 'titles': title, 'rvstart': ts + 'T00:00:00Z',
            'rvdir': 'older', 'rvlimit': 1, 'rvprop': 'timestamp|content', 'rvslots': 'main',
            'format': 'json', 'formatversion': 2})
        try:
            rev = r.json()['query']['pages'][0]['revisions'][0]
            text = rev['slots']['main']['content']
            slug = 'tsx60' if '60' in title else 'composite'
            open(f'research/tsx60/{slug}_{ts}.wiki', 'w').write(f"<!-- revision {rev['timestamp']} -->\n" + text)
            print(title, ts, rev['timestamp'], len(text))
        except Exception as exc:
            print('failed', title, ts, exc, r.text[:200])
