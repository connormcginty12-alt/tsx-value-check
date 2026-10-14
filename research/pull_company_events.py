"""One-off research pull: dividend history, share-count history and analyst rating changes."""
import pandas as pd
import yfinance as yf

names = pd.read_csv('names.csv')
tickers = [t for t in names.tsx_ticker if t.endswith(('.TO', '.V'))]
# US listings of interlisted names (richer analyst coverage on Yahoo)
US = {'RY.TO': 'RY', 'TD.TO': 'TD', 'BMO.TO': 'BMO', 'BNS.TO': 'BNS', 'CM.TO': 'CM', 'SHOP.TO': 'SHOP',
      'CNQ.TO': 'CNQ', 'ENB.TO': 'ENB', 'AEM.TO': 'AEM', 'SU.TO': 'SU', 'BN.TO': 'BN', 'CP.TO': 'CP',
      'BAM.TO': 'BAM', 'CNR.TO': 'CNI', 'MFC.TO': 'MFC', 'ABX.TO': 'B', 'TRP.TO': 'TRP', 'IMO.TO': 'IMO',
      'WPM.TO': 'WPM', 'CVE.TO': 'CVE', 'FNV.TO': 'FNV', 'TRI.TO': 'TRI', 'CLS.TO': 'CLS', 'SLF.TO': 'SLF',
      'CCO.TO': 'CCJ', 'NTR.TO': 'NTR', 'TECK-B.TO': 'TECK', 'QSR.TO': 'QSR', 'PPL.TO': 'PBA', 'K.TO': 'KGC',
      'FTS.TO': 'FTS', 'PAAS.TO': 'PAAS', 'BCE.TO': 'BCE', 'MG.TO': 'MGA', 'RCI-B.TO': 'RCI', 'RBA.TO': 'RBA',
      'GFL.TO': 'GFL', 'GIB-A.TO': 'GIB', 'AGI.TO': 'AGI', 'EQX.TO': 'EQX', 'T.TO': 'TU', 'HBM.TO': 'HBM',
      'IMG.TO': 'IAG', 'HUT.TO': 'HUT', 'TFII.TO': 'TFII', 'AG.TO': 'AG', 'GIL.TO': 'GIL', 'STN.TO': 'STN',
      'CAE.TO': 'CAE', 'DSG.TO': 'DSGX', 'SSRM.TO': 'SSRM', 'BTO.TO': 'BTG', 'ELD.TO': 'EGO', 'SOBO.TO': 'SOBO'}

div, shares, ud = [], [], []
for t in tickers:
    tk = yf.Ticker(t)
    try:
        s = tk.dividends
        if s is not None and len(s):
            div.append(pd.DataFrame({'ticker': t, 'date': s.index.tz_localize(None).date, 'dividend': s.values}))
    except Exception as exc:
        print('div failed', t, exc)
    try:
        s = tk.get_shares_full(start='2012-01-01')
        if s is not None and len(s):
            shares.append(pd.DataFrame({'ticker': t, 'date': s.index.tz_localize(None).date, 'shares': s.values}))
    except Exception as exc:
        print('shares failed', t, exc)
    for sym in [t] + ([US[t]] if t in US else []):
        try:
            u = yf.Ticker(sym).upgrades_downgrades
            if u is not None and len(u):
                u = u.reset_index()
                u['ticker'] = t
                u['source_symbol'] = sym
                ud.append(u)
        except Exception as exc:
            print('ud failed', sym, exc)
for name, rows in [('dividends', div), ('shares', shares), ('analyst_actions', ud)]:
    if rows:
        pd.concat(rows).to_csv(f'research/{name}.csv', index=False)
    print(name, len(rows), 'tickers')
