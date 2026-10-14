"""One-off research pull: 5 years of daily volume and earnings history for the stock list."""
import pandas as pd
import yfinance as yf

names = pd.read_csv('names.csv')
tickers = [t for t in names.tsx_ticker if t.endswith(('.TO', '.V'))]

data = yf.download(tickers, period='5y', interval='1d', auto_adjust=True, progress=False, threads=True)
data['Volume'].to_csv('research/volume.csv', index_label='date')
data['Open'].to_csv('research/open.csv', index_label='date')
data['Close'].to_csv('research/close.csv', index_label='date')

rows = []
for t in tickers:
    try:
        ed = yf.Ticker(t).get_earnings_dates(limit=28)
        if ed is None or ed.empty:
            print('no earnings dates:', t)
            continue
        ed = ed.reset_index()
        ed.columns = ['datetime', 'eps_estimate', 'eps_reported', 'surprise_pct'][:len(ed.columns)]
        ed['ticker'] = t
        rows.append(ed)
    except Exception as exc:
        print('failed:', t, exc)
if rows:
    pd.concat(rows).to_csv('research/earnings.csv', index=False)
print('done', len(rows), 'tickers with earnings history')
