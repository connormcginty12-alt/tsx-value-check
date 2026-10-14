"""Portfolio backtest engine.

Decide at the close of day t using only data known then, trade at the close of t+1,
pay costs on every dollar traded, let weights drift between rebalances.
"""
import numpy as np
import pandas as pd

g = pd.read_pickle('/home/claude/fund/base.pkl')
P = g['P']; stocks = g['stocks']; sec = g['sec']
RET = P.pct_change(fill_method=None)          # daily simple total returns (adjusted closes)
IDX = RET.index
BM = pd.read_csv('/home/claude/repo/research/benchmarks.csv', index_col=0, parse_dates=True).reindex(IDX).ffill()
XIC = BM['XIC.TO'].pct_change(fill_method=None).fillna(0)


def run(score, n=20, every=5, cost_bp=10, start='2015-01-01', end='2026-10-13', buffer=None,
        universe=None, sector_cap=None, trend_filter=False, side='long', weighting='equal'):
    """score: DataFrame (dates x stocks), higher = more underpriced.
    buffer: keep a holding until its rank falls out of the top `buffer` (reduces trading).
    universe: optional boolean DataFrame of eligible stocks per date.
    sector_cap: max holdings per sector.
    trend_filter: hold cash (0% return) when the TSX ETF is below its 200-day average.
    side: 'long' (top n), 'short' (bottom n, returned as the negated return), 'longshort'."""
    dates = IDX[(IDX >= start) & (IDX <= end)]
    xic_px = BM['XIC.TO']
    above = (xic_px > xic_px.rolling(200).mean())
    w = pd.Series(0.0, index=stocks)
    out_ret, out_to, out_n = [], [], []
    pending = None
    for k, d in enumerate(dates):
        # 1. today's return on yesterday's weights (weights drift)
        r = RET.loc[d].reindex(stocks).fillna(0.0)
        day_ret = float((w * r).sum())
        if w.abs().sum() > 0:
            w = w * (1 + r)
            gross = w[w > 0].sum() + (-w[w < 0]).sum()
            # keep long and short books at their drifted sizes; renormalise only at rebalance
        to = 0.0
        # 2. execute the order decided yesterday, at today's close
        if pending is not None:
            target = pending
            to = float((target - w).abs().sum())
            day_ret -= to * cost_bp / 1e4
            w = target.copy()
            pending = None
        out_ret.append(day_ret); out_to.append(to); out_n.append(int((w != 0).sum()))
        # 3. decide at today's close
        if k % every == 0:
            s = score.loc[d].dropna() if d in score.index else pd.Series(dtype=float)
            if universe is not None:
                elig = universe.loc[d]
                s = s[s.index.isin(elig[elig].index)]
            s = s[P.loc[d, s.index].notna()]
            if len(s) < max(30, 2 * n):
                continue
            tgt = pd.Series(0.0, index=stocks)
            invested = not (trend_filter and not bool(above.get(d, True)))

            def pick(series, cur):
                ranked = series.sort_values(ascending=False)
                chosen = []
                if buffer:
                    keep_zone = set(ranked.index[:buffer])
                    chosen = [x for x in cur if x in keep_zone]
                per_sec = {}
                for x in chosen:
                    per_sec[sec[x]] = per_sec.get(sec[x], 0) + 1
                for x in ranked.index:
                    if len(chosen) >= n:
                        break
                    if x in chosen:
                        continue
                    if sector_cap and per_sec.get(sec[x], 0) >= sector_cap:
                        continue
                    chosen.append(x); per_sec[sec[x]] = per_sec.get(sec[x], 0) + 1
                return chosen[:n]

            if invested:
                if side in ('long', 'longshort'):
                    cur = list(w[w > 0].index)
                    L = pick(s, cur)
                    tgt[L] = 1.0 / len(L) if side == 'long' else 0.5 / len(L)
                if side in ('short', 'longshort'):
                    cur = list(w[w < 0].index)
                    S = pick(-s, cur)
                    tgt[S] = -(1.0 if side == 'short' else 0.5) / len(S)
            pending = tgt
    res = pd.DataFrame({'ret': out_ret, 'turnover': out_to, 'holdings': out_n}, index=dates)
    return res


def equal_weight(start='2015-01-01', end='2026-10-13'):
    dates = IDX[(IDX >= start) & (IDX <= end)]
    r = RET.loc[dates, stocks]
    return r.mean(axis=1).fillna(0)


def stats(r, bench=None):
    r = r.dropna()
    yrs = len(r) / 252
    eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(252)
    dd = (eq / eq.cummax() - 1).min()
    out = {'CAGR_%': cagr * 100, 'vol_%': vol * 100, 'sharpe': (r.mean() * 252) / vol if vol else np.nan,
           'max_drawdown_%': dd * 100, 'total_x': eq.iloc[-1]}
    if bench is not None:
        b = bench.reindex(r.index).fillna(0)
        ex = r - b
        out['excess_%yr'] = ex.mean() * 252 * 100
        out['tracking_err_%'] = ex.std() * np.sqrt(252) * 100
        out['info_ratio'] = (ex.mean() * 252) / (ex.std() * np.sqrt(252))
        yr = (1 + r).groupby(r.index.year).prod() - 1
        yb = (1 + b).groupby(b.index.year).prod() - 1
        out['years_beat'] = f'{int((yr > yb).sum())}/{len(yr)}'
        out['beta'] = np.cov(r, b)[0, 1] / b.var()
    return out
