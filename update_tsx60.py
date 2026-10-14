"""Refresh tsx60_members.csv from Wikipedia's current S&P/TSX 60 article.

Keeps the previous file if the fetch or parse fails (so the daily job never breaks on it).
Columns: tsx_symbol (as listed), yahoo (Yahoo Finance symbol), company, gics_sector.
"""
import re

import pandas as pd
import requests

API = 'https://en.wikipedia.org/w/api.php'
HDR = {'User-Agent': 'tsx-value-check (github actions; personal research)'}


def to_yahoo(sym):
    return sym.replace('.', '-') + '.TO'


def fetch():
    r = requests.get(API, headers=HDR, timeout=30, params={
        'action': 'query', 'prop': 'revisions', 'titles': 'S&P/TSX 60', 'rvlimit': 1,
        'rvprop': 'timestamp|content', 'rvslots': 'main', 'format': 'json', 'formatversion': 2})
    rev = r.json()['query']['pages'][0]['revisions'][0]
    text = rev['slots']['main']['content']
    rows = []
    # one table row per "|-" block; the first cell holds the symbol (template or plain text)
    for block in text.split('\n|-'):
        cells = [c.strip() for c in re.split(r'\n\||\|\|', block) if c.strip()]
        if len(cells) < 3:
            continue
        m = re.search(r'\{\{\s*(?:TSX link|tsx|TSX)\s*\|\s*([A-Z0-9.\-]+)\s*\}\}', cells[0]) or \
            re.fullmatch(r'([A-Z][A-Z0-9.\-]{0,9})', re.sub(r'[\[\]{}]', '', cells[0]))
        if not m:
            continue
        sym = m.group(1)
        name = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', r'\1', cells[1])
        name = re.sub(r'<[^>]+>|\{\{[^}]*\}\}', '', name).strip()
        sector = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', r'\1', cells[2])
        sector = re.sub(r'<[^>]+>|\{\{[^}]*\}\}', '', sector).strip()
        rows.append({'tsx_symbol': sym, 'yahoo': to_yahoo(sym), 'company': name, 'gics_sector': sector})
    df = pd.DataFrame(rows).drop_duplicates('tsx_symbol')
    return rev['timestamp'], df


if __name__ == '__main__':
    try:
        ts, df = fetch()
        if 50 <= len(df) <= 65:
            df.to_csv('tsx60_members.csv', index=False)
            print(f'TSX 60 members: {len(df)} (Wikipedia revision {ts})')
        else:
            print(f'Parsed {len(df)} rows — not saving; keeping previous tsx60_members.csv')
            print(df.head(10).to_string())
    except Exception as exc:
        print('TSX 60 refresh failed; keeping previous file:', exc)
