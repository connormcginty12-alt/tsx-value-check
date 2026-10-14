"""Prices + earnings for every S&P/TSX 60 member since 2014, trying old and current Yahoo symbols."""
import json
import pandas as pd
import yfinance as yf

ALIASES = {'BAM.A': ['BN.TO', 'BAM-A.TO'], 'SLW': ['WPM.TO', 'SLW.TO'], 'SNC': ['ATRL.TO', 'SNC.TO'],
           'VRX': ['BHC.TO', 'VRX.TO'], 'TCK.B': ['TECK-B.TO'], 'ATD.B': ['ATD.TO', 'ATD-B.TO'],
           'PWT': ['OBE.TO', 'PWT.TO'], 'CPG': ['VRN.TO', 'CPG.TO'], 'ECA': ['OVV.TO', 'ECA.TO'],
           'AGU': ['AGU.TO'], 'POT': ['POT.TO'], 'BPY.UN': ['BPY-UN.TO'], 'WEED': ['WEED.TO']}
tick = set()
for f in __import__('glob').glob('research/tsx60/tsx60_*.wiki'):
    import re
    tick |= set(re.findall(r'\{\{TSX link\|([A-Z0-9.\-]+)\}\}', open(f).read()))
found, closes, earn = {}, {}, []
for t in sorted(tick):
    cands = ALIASES.get(t, []) + [t.replace('.', '-') + '.TO']
    for c in dict.fromkeys(cands):
        try:
            s = yf.download(c, start='2012-01-01', auto_adjust=True, progress=False)['Close']
            s = s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s
            if s.notna().sum() > 250:
                closes[t] = s; found[t] = c
                try:
                    ed = yf.Ticker(c).get_earnings_dates(limit=60)
                    if ed is not None and not ed.empty:
                        ed = ed.reset_index().iloc[:, :4]
                        ed.columns = ['datetime', 'eps_estimate', 'eps_reported', 'surprise_pct']
                        ed['wiki_ticker'] = t
                        earn.append(ed)
                except Exception as exc:
                    print('earnings failed', c, exc)
                break
        except Exception as exc:
            print('price failed', c, exc)
    print(t, '->', found.get(t, 'NOT FOUND'))
pd.DataFrame(closes).to_csv('research/hist_close.csv', index_label='date')
if earn:
    pd.concat(earn).to_csv('research/hist_earnings.csv', index=False)
fx = yf.download(['CAD=X', '^GSPTSE'], start='2012-01-01', auto_adjust=True, progress=False)['Close']
fx.to_csv('research/hist_factors.csv', index_label='date')
json.dump(found, open('research/hist_symbol_map.json', 'w'), indent=1)
print('found', len(found), 'of', len(tick))
