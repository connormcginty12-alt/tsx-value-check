"""Grade the ratings against what actually happened, like ConCast vs the gauge.

- Appends today's ratings.csv to ratings_history.csv (the live record; never rewritten).
- For every rating date with a full week of prices since, measures:
    * rank correlation between score and the following week's return vs the group
      (traded at the next day's close, held 5 days -- as in the backtest)
    * average next-week return of Underpriced, Overpriced, and the gap between them
    * forecast error: |forecast_1w - actual close 5 trading days later|, vs the
      'no change' forecast (today's close), as % of price
- Dates before live tracking began are graded from scores_history.csv and marked 'backfill'
  (those use a model chosen with data that includes them, so they flatter it).
Writes scorecard.csv (one row per rating date) and scorecard_summary.csv.
"""
import os

import numpy as np
import pandas as pd

px = pd.read_csv('tsx100_closes.csv', index_col=0, parse_dates=True)
px = px[px['^GSPTSE'].notna()]
px.columns = [c.replace('.TO', '').replace('.V', '') for c in px.columns]
days = px.index

# 1. live record
today = pd.read_csv('ratings.csv', keep_default_na=False)
keep = ['as_of', 'ticker', 'score', 'rating', 'close', 'forecast_1w']
if os.path.exists('ratings_history.csv'):
    hist = pd.read_csv('ratings_history.csv', keep_default_na=False)
    hist = hist[hist.as_of != today.as_of.iloc[0]]
    hist = pd.concat([hist, today[keep]], ignore_index=True)
else:
    hist = today[keep].copy()
hist.to_csv('ratings_history.csv', index=False)
hist['source'] = 'live'

# 2. backfill for dates before live tracking began
first_live = hist.as_of.min()
if os.path.exists('scores_history.csv'):
    back = pd.read_csv('scores_history.csv', keep_default_na=False)
    back = back[back.as_of < first_live]
    back['source'] = 'backfill'
    allr = pd.concat([back, hist], ignore_index=True)
else:
    allr = hist

# 3. grade
rows = []
for d, grp in allr.groupby('as_of'):
    i = days.searchsorted(pd.Timestamp(d))
    if i >= len(days) or days[i] != pd.Timestamp(d) or i + 6 >= len(days):
        continue   # not a trading day in our data, or the week hasn't finished yet
    g = grp[grp.ticker.isin(px.columns)].copy()
    g['p0'] = px.iloc[i][g.ticker].values          # close on the rating date
    g['actual_5d'] = px.iloc[i + 5][g.ticker].values  # close 5 trading days later (forecast target)
    g['ret'] = np.log(px.iloc[i + 6][g.ticker].values / px.iloc[i + 1][g.ticker].values)
    g = g[np.isfinite(g.ret) & np.isfinite(g.actual_5d) & np.isfinite(g.p0)]
    g['rel'] = g.ret - g.ret.mean()
    g['score'] = pd.to_numeric(g.score)
    f = pd.to_numeric(g.forecast_1w, errors='coerce')
    rows.append({
        'as_of': d, 'source': g.source.iloc[0], 'stocks': len(g),
        'rank_corr': g.score.rank().corr(g.rel.rank()),
        'underpriced_pct': g.loc[g.rating == 'Underpriced', 'rel'].mean() * 100,
        'overpriced_pct': g.loc[g.rating == 'Overpriced', 'rel'].mean() * 100,
        'forecast_error_pct': (abs(f - g.actual_5d) / g.p0).mean() * 100,
        'no_change_error_pct': (abs(g.p0 - g.actual_5d) / g.p0).mean() * 100,
    })
sc = pd.DataFrame(rows)
if len(sc):
    sc['gap_pct'] = sc.underpriced_pct - sc.overpriced_pct
    sc['forecast_beats_no_change'] = np.where(sc.forecast_error_pct < sc.no_change_error_pct, 'Yes', 'No')
    sc = sc.round(4)
sc.to_csv('scorecard.csv', index=False)

summ = []
for src in ['live', 'backfill']:
    s = sc[sc.source == src] if len(sc) else sc
    if len(s) == 0:
        summ.append({'source': src, 'rating_dates': 0})
        continue
    wk = s.iloc[::5]   # non-overlapping weeks
    summ.append({'source': src, 'rating_dates': len(s), 'first': s.as_of.min(), 'last': s.as_of.max(),
                 'avg_rank_corr': s.rank_corr.mean(), 'weeks_corr_positive_pct': (wk.rank_corr > 0).mean() * 100,
                 'avg_weekly_gap_pct': s.gap_pct.mean(), 'weeks_gap_positive_pct': (wk.gap_pct > 0).mean() * 100,
                 'avg_forecast_error_pct': s.forecast_error_pct.mean(), 'avg_no_change_error_pct': s.no_change_error_pct.mean()})
pd.DataFrame(summ).round(3).to_csv('scorecard_summary.csv', index=False)
print(pd.DataFrame(summ).round(3).to_string(index=False))
