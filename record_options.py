"""Daily option-chain recorder (free, Yahoo Finance) — builds our own options history.

For each stock: its Toronto listing (if Yahoo carries Montreal Exchange options for it) and its
US listing for interlisted names. Keeps expiries within ~120 days and strikes within ±30% of the
stock price, to keep files small. Writes data/options/YYYY-MM-DD.csv.gz and prints coverage.
"""
import datetime as dt
import os

import pandas as pd
import yfinance as yf

US = {'RY.TO': 'RY', 'TD.TO': 'TD', 'BMO.TO': 'BMO', 'BNS.TO': 'BNS', 'CM.TO': 'CM', 'SHOP.TO': 'SHOP',
      'CNQ.TO': 'CNQ', 'ENB.TO': 'ENB', 'AEM.TO': 'AEM', 'SU.TO': 'SU', 'BN.TO': 'BN', 'CP.TO': 'CP',
      'BAM.TO': 'BAM', 'CNR.TO': 'CNI', 'MFC.TO': 'MFC', 'ABX.TO': 'B', 'TRP.TO': 'TRP', 'IMO.TO': 'IMO',
      'WPM.TO': 'WPM', 'CVE.TO': 'CVE', 'FNV.TO': 'FNV', 'TRI.TO': 'TRI', 'CLS.TO': 'CLS', 'SLF.TO': 'SLF',
      'CCO.TO': 'CCJ', 'NTR.TO': 'NTR', 'TECK-B.TO': 'TECK', 'QSR.TO': 'QSR', 'PPL.TO': 'PBA', 'K.TO': 'KGC',
      'FTS.TO': 'FTS', 'PAAS.TO': 'PAAS', 'BCE.TO': 'BCE', 'MG.TO': 'MGA', 'RCI-B.TO': 'RCI', 'RBA.TO': 'RBA',
      'GFL.TO': 'GFL', 'GIB-A.TO': 'GIB', 'AGI.TO': 'AGI', 'EQX.TO': 'EQX', 'T.TO': 'TU', 'HBM.TO': 'HBM',
      'IMG.TO': 'IAG', 'HUT.TO': 'HUT', 'TFII.TO': 'TFII', 'AG.TO': 'AG', 'GIL.TO': 'GIL', 'STN.TO': 'STN',
      'CAE.TO': 'CAE', 'DSG.TO': 'DSGX', 'SSRM.TO': 'SSRM', 'BTO.TO': 'BTG', 'ELD.TO': 'EGO', 'SOBO.TO': 'SOBO',
      'OTEX.TO': 'OTEX', 'WCN.TO': 'WCN', 'FSV.TO': 'FSV', 'BIP-UN.TO': 'BIP', 'BBD-B.TO': None}
MAX_DAYS, BAND = 120, 0.30
today = dt.date.today()
os.makedirs('data/options', exist_ok=True)
names = pd.read_csv('names.csv')
tickers = [t for t in names.tsx_ticker if str(t).endswith(('.TO', '.V'))]

rows, cover = [], []
for t in tickers:
    for sym, venue in [(t, 'TSX/MX'), (US.get(t), 'US')]:
        if not sym:
            continue
        try:
            tk = yf.Ticker(sym)
            exps = [e for e in (tk.options or ()) if (dt.date.fromisoformat(e) - today).days <= MAX_DAYS]
        except Exception as exc:
            cover.append({'ticker': t, 'symbol': sym, 'venue': venue, 'expiries': 0, 'contracts': 0, 'error': str(exc)[:80]})
            continue
        n = 0
        try:
            spot = tk.fast_info.get('last_price') or tk.fast_info.get('lastPrice')
        except Exception:
            spot = None
        for e in exps:
            try:
                ch = tk.option_chain(e)
            except Exception:
                continue
            for kind, df in (('call', ch.calls), ('put', ch.puts)):
                if df is None or df.empty:
                    continue
                df = df.copy()
                if spot:
                    df = df[(df.strike >= spot * (1 - BAND)) & (df.strike <= spot * (1 + BAND))]
                df['ticker'], df['symbol'], df['venue'], df['type'], df['expiry'] = t, sym, venue, kind, e
                df['spot'] = spot
                df['snapshot_date'] = today.isoformat()
                rows.append(df[['snapshot_date', 'ticker', 'symbol', 'venue', 'spot', 'type', 'expiry', 'strike',
                                'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility',
                                'lastTradeDate']])
                n += len(df)
        cover.append({'ticker': t, 'symbol': sym, 'venue': venue, 'expiries': len(exps), 'contracts': n, 'error': ''})

cv = pd.DataFrame(cover)
cv.to_csv('data/options_coverage.csv', index=False)
if rows:
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(f'data/options/{today.isoformat()}.csv.gz', index=False, compression='gzip')
    print('contracts saved:', len(out))
print('symbols with options:', (cv.contracts > 0).sum(), 'of', len(cv))
print(cv.groupby('venue').apply(lambda x: f"{(x.contracts > 0).sum()}/{len(x)} symbols, {x.contracts.sum()} contracts"))
