"""Daily recorder: builds our own history of data that has no free archive.

1. Analyst estimate snapshots from Yahoo (consensus EPS now vs 7/30/60/90 days ago,
   number of up/down revisions, price targets) -> data/estimates_history.csv (appended daily)
2. CIRO Consolidated Short Position Reports (twice monthly) -> data/short_positions/raw/*.xls
   and a combined data/short_positions.csv
"""
import datetime as dt
import io
import os

import pandas as pd
import requests
import yfinance as yf

os.makedirs('data/short_positions/raw', exist_ok=True)
today = dt.date.today()
names = pd.read_csv('names.csv')
tickers = [t for t in names.tsx_ticker if t.endswith(('.TO', '.V'))]

# ---------- 1. Estimate snapshots ----------
rows = []
for t in tickers:
    tk = yf.Ticker(t)
    base = {'snapshot_date': today.isoformat(), 'ticker': t}
    try:
        trend = tk.eps_trend
        if trend is not None and not trend.empty:
            for period, r in trend.iterrows():
                rows.append({**base, 'kind': 'eps_trend', 'period': period, **r.to_dict()})
    except Exception as exc:
        print('eps_trend failed', t, exc)
    try:
        rev = tk.eps_revisions
        if rev is not None and not rev.empty:
            for period, r in rev.iterrows():
                rows.append({**base, 'kind': 'eps_revisions', 'period': period, **r.to_dict()})
    except Exception as exc:
        print('eps_revisions failed', t, exc)
    try:
        pt = tk.analyst_price_targets
        if pt:
            rows.append({**base, 'kind': 'price_target', 'period': '', **pt})
    except Exception as exc:
        print('price targets failed', t, exc)
if rows:
    snap = pd.DataFrame(rows)
    path = 'data/estimates_history.csv'
    if os.path.exists(path):
        old = pd.read_csv(path)
        old = old[old.snapshot_date != today.isoformat()]   # re-runs on the same day replace
        snap = pd.concat([old, snap], ignore_index=True)
    snap.to_csv(path, index=False)
    print('estimate snapshot rows today:', len(rows))

# ---------- 2. CIRO short position reports ----------
def report_dates(start, end):
    d = dt.date(start.year, start.month, 1)
    while d <= end:
        nxt = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        for day in (dt.date(d.year, d.month, 15), nxt - dt.timedelta(days=1)):
            if start <= day <= end:
                yield day
        d = nxt

raw_dir = 'data/short_positions/raw'
have = set(os.listdir(raw_dir))
start = dt.date(2019, 1, 1)
fetched = 0
for day in report_dates(start, today):
    # reports are stamped on the 15th / month-end, or the last business day before it
    for back in range(0, 4):
        d = day - dt.timedelta(days=back)
        fname = f'{d:%Y%m%d}_CSPR_Report.xls'
        if fname in have:
            break
        url = f'https://www.ciro.ca/sites/default/files/epubs/CSPR/{fname}'
        try:
            r = requests.get(url, timeout=30)
        except Exception as exc:
            print('request failed', url, exc)
            continue
        if r.status_code == 200 and len(r.content) > 1000:
            open(os.path.join(raw_dir, fname), 'wb').write(r.content)
            have.add(fname)
            fetched += 1
            break
print('short reports fetched this run:', fetched, '| total on file:', len(have))

frames = []
for fname in sorted(have):
    try:
        x = pd.read_excel(os.path.join(raw_dir, fname), header=None)
    except Exception as exc:
        print('could not read', fname, exc)
        continue
    # find the header row (contains a "symbol" column)
    hdr = next((i for i in range(min(30, len(x)))
                if x.iloc[i].astype(str).str.contains('symbol', case=False).any()), None)
    if hdr is None:
        print('no header found in', fname, x.head(3).values.tolist())
        continue
    x.columns = [str(c).strip() for c in x.iloc[hdr]]
    x = x.iloc[hdr + 1:].dropna(how='all')
    x.insert(0, 'report_date', pd.to_datetime(fname[:8]).date())
    frames.append(x)
if frames:
    sp = pd.concat(frames, ignore_index=True)
    sp.to_csv('data/short_positions.csv', index=False)
    print('short position rows:', len(sp), 'columns:', list(sp.columns))
