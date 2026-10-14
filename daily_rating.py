"""Rate each stock as underpriced / fairly priced / overpriced.

Inputs: tsx100_closes.csv, earnings.csv, financials.csv (from pull_tsx_prices.py).
Score = average of four cross-sectional z-scores, each of which predicted next-week
returns in both 2014-2020 and 2021-2026 (positive in every year 2014-2026 combined):
  1. 1-month pullback: minus the stock's last-21-trading-day return
  2. Peer momentum: return over the past 12 months excluding the last month,
     after removing market beta and sector peers' moves
  3. Earnings surprise: reported vs expected EPS at the latest report (last 63 trading days)
  4. Earnings-day reaction: the stock's move vs peers on the two days after its latest
     report (last 63 trading days) -- markets under-react to earnings news
Top fifth = Underpriced, bottom fifth = Overpriced. Current financials are reported for
context only; valuation ratios flipped sign between periods so they are not in the score.
Writes ratings.csv.
"""
import numpy as np
import pandas as pd

SECTORS = {
    'Banks': 'RY TD BMO BNS CM NA',
    'Insurance & asset mgmt': 'MFC GWO SLF POW IFC FFH IGM IAG X BN BAM',
    'Oil & gas producers': 'CNQ SU IMO CVE TOU WCP',
    'Pipelines': 'ENB TRP PPL KEY ALA SOBO',
    'Utilities & REIT': 'FTS H EMA CU CPX CHP-UN',
    'Gold & silver': 'AEM ABX WPM FNV K PAAS LUG AGI EQX CGG IMG GMIN ELD DPM AG DSV BTO SSRM',
    'Base metals': 'TECK-B FM LUN HBM IVN CS',
    'Fertilizer, uranium, packaging': 'NTR CCO CCL-B',
    'Rail & trucking': 'CP CNR TFII',
    'Industrials': 'BBD-B WSP GFL RBA TIH ATRL FTT STN CAE',
    'Tech': 'SHOP CSU CLS GIB-A TOI DSG HUT TRI',
    'Telecom': 'BCE RCI-B T QBR-B',
    'Staples & retail': 'L ATD WN MRU SAP EMP-A DOL',
    'Consumer discretionary': 'QSR MG ATZ GIL CTC-A',
}
SEC = {t + ('.V' if t == 'TOI' else '.TO'): s for s, ts in SECTORS.items() for t in ts.split()}

d = pd.read_csv('tsx100_closes.csv', index_col=0, parse_dates=True)
days = d['^GSPTSE'].dropna().index
P = d.reindex(days)
stocks = [s for s in SEC if s in P and P[s].notna().sum() > 300]
LP = np.log(P[stocks])
R = LP.diff().iloc[1:]
TSX = np.log(P['^GSPTSE']).diff().iloc[1:]
LP = LP.iloc[1:]

# Market-adjusted, peer-relative daily residuals (beta known only from past data)
beta = pd.DataFrame({s: R[s].rolling(252, min_periods=120).cov(TSX) / TSX.rolling(252, min_periods=120).var()
                     for s in stocks}).shift(1)
e = R - beta.mul(TSX, axis=0)
res = pd.DataFrame({s: e[s] - e[[p for p in stocks if SEC[p] == SEC[s] and p != s]].mean(axis=1)
                    for s in stocks})
cr = res.cumsum()

pullback_1m = -(LP - LP.shift(21))
peer_mom = cr.shift(21) - cr.shift(252)

def z(x):
    return x.sub(x.mean(axis=1), axis=0).div(x.std(axis=1), axis=0).clip(-3, 3)

# --- Earnings signals (point in time) ---
E = pd.read_csv('earnings.csv').dropna(subset=['eps_reported', 'eps_estimate'])
E['dt'] = pd.to_datetime(E.datetime, utc=True).dt.tz_convert('America/Toronto')
idx = LP.index

def eff_day(ts):
    """First trading day the market could react: same day if before 9:30 am, else next."""
    d0 = pd.Timestamp(ts.date())
    i = idx.searchsorted(d0 if ts.hour + ts.minute / 60 < 9.5 else d0 + pd.Timedelta(days=1))
    return idx[i] if i < len(idx) else pd.NaT

E['eff'] = E.dt.map(eff_day)
E = E.dropna(subset=['eff']).sort_values('eff').drop_duplicates(['ticker', 'eff'], keep='last')
E['sue'] = ((E.eps_reported - E.eps_estimate) / E.eps_estimate.abs().clip(lower=0.05)).clip(-1, 1)
sue = pd.DataFrame(np.nan, index=idx, columns=stocks)
ear = pd.DataFrame(np.nan, index=idx, columns=stocks)
cres = res.fillna(0).cumsum()
for t, grp in E.groupby('ticker'):
    if t not in stocks:
        continue
    for dt, sv in zip(grp.eff, grp.sue):
        i = idx.get_loc(dt)
        sue.iloc[i, sue.columns.get_loc(t)] = sv
        if i + 1 < len(idx):   # reaction = residual on report day and next day, known after day 2
            ear.iloc[i + 1, ear.columns.get_loc(t)] = cres[t].iloc[i + 1] - cres[t].iloc[i - 1]
sue = sue.ffill(limit=62)
ear = ear.ffill(limit=62)

def zf(x):   # z-score; stocks with no recent report count as neutral (0)
    return z(x).fillna(0).where(LP.notna())

score = ((z(pullback_1m).fillna(0) + z(peer_mom).fillna(0) + zf(sue) + zf(ear)) / 4).where(
    pullback_1m.notna() & peer_mom.notna())

# Calibrate: average next-week return vs the group per unit of score, non-overlapping weeks
fwd = LP.shift(-5) - LP
fwd = fwd.sub(fwd.mean(axis=1), axis=0)
wk = fwd.index[260:-5:5]
xs, ys = score.loc[wk].stack(), fwd.loc[wk].stack()
xs, ys = xs.align(ys, join='inner')
ok = np.isfinite(xs) & np.isfinite(ys)
slope = np.polyfit(xs[ok], ys[ok], 1)[0]

t = score.index[-1]
names = pd.read_csv('names.csv').set_index('tsx_ticker').company
out = pd.DataFrame({'score': score.loc[t], 'past_1m_pct': -pullback_1m.loc[t] * 100,
                    'peer_1y_pct': peer_mom.loc[t] * 100, 'eps_surprise_pct': sue.loc[t] * 100,
                    'earnings_reaction_pct': ear.loc[t] * 100}).dropna(subset=['score'])
out['exp_rel_1w_pct'] = out.score * slope * 100
q = pd.qcut(out.score.rank(method='first'), 5, labels=False)
out['rating'] = np.select([q == 4, q == 0], ['Underpriced', 'Overpriced'], 'Fairly priced')
out['ticker'] = [s.replace('.TO', '').replace('.V', '') for s in out.index]
out['company'] = out.index.map(names)
out['sector'] = out.index.map(SEC)
out['as_of'] = str(t.date())
out = out.sort_values('score', ascending=False)
fin = pd.read_csv('financials.csv').set_index('ticker')
out['pe_trailing'] = out.index.map(fin.trailingPE)
out['pe_forward'] = out.index.map(fin.forwardPE)
out['price_to_book'] = out.index.map(fin.priceToBook)
out['roe_pct'] = out.index.map(fin.returnOnEquity) * 100
out['revenue_growth_pct'] = out.index.map(fin.revenueGrowth) * 100
out['debt_to_equity'] = out.index.map(fin.debtToEquity)
cols = ['ticker', 'company', 'sector', 'rating', 'score', 'exp_rel_1w_pct', 'past_1m_pct', 'peer_1y_pct',
        'eps_surprise_pct', 'earnings_reaction_pct', 'pe_trailing', 'pe_forward', 'price_to_book', 'roe_pct',
        'revenue_growth_pct', 'debt_to_equity', 'as_of']
out[cols].round(2).to_csv('ratings.csv', index=False)
print(f'Rated {len(out)} stocks as of {t.date()}')
