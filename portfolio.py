"""Paper portfolio: the backtested rule, run live.

Rule (as in research/backtest): hold the 10 S&P/TSX 60 stocks with the highest score, equal weight.
Rebalance once a week at the close of the week's first trading day, using the previous trading day's
scores (normally Friday's). Sell anything that dropped out of the top 10, buy what came in, reset
all ten to equal weight. Trading costs: 0.10% of every dollar traded. Benchmark: XIU (TSX 60 ETF).
Values are total return (dividends credited), measured from Yahoo's dividend-adjusted closes: each
position is worth basis x (adjusted close now / adjusted close on the day it was last sized).

Runs daily after daily_rating.py. State lives in portfolio_holdings.csv and portfolio_state.json.
Outputs: portfolio_summary.csv, portfolio_now.csv (holdings), portfolio_plan.csv (provisional
buy/hold/sell for the next rebalance), portfolio_value.csv (daily value vs XIU), portfolio_trades.csv.
"""
import datetime as dt
import json
import os

import numpy as np
import pandas as pd

START = pd.Timestamp('2026-10-14')   # first buy at this close (no back-dating)
N = 10
COST = 0.0010
CAPITAL = 10000.0

px = pd.read_csv('tsx100_closes.csv', index_col=0, parse_dates=True)
px = px[px['^GSPTSE'].notna()]
days = px.index
t = days[-1]
prev = days[-2]
members = pd.read_csv('tsx60_members.csv')
names = dict(zip(members.yahoo, members.company))
rat = pd.read_csv('ratings.csv', keep_default_na=False)
rating_of = dict(zip(rat.ticker, rat.rating))
sc = pd.read_csv('portfolio_scores.csv', parse_dates=['date'])
sc = sc[sc.yahoo.isin(members.yahoo)]
short = lambda y: y.replace('.TO', '').replace('.V', '')


def ranking(day):
    s = sc[sc.date == day].set_index('yahoo').score
    s = s[[y for y in s.index if y in px and pd.notna(px.at[t, y])]]
    return s.sort_values(ascending=False)


state = json.load(open('portfolio_state.json')) if os.path.exists('portfolio_state.json') else {}
hold = (pd.read_csv('portfolio_holdings.csv') if os.path.exists('portfolio_holdings.csv')
        else pd.DataFrame(columns=['yahoo', 'shares', 'entry_date', 'entry_price', 'basis', 'basis_date']))
if 'basis' not in hold:   # files written before dividends were credited
    hold['basis'] = hold.shares * hold.entry_price
    hold['basis_date'] = hold.entry_date
trades = (pd.read_csv('portfolio_trades.csv') if os.path.exists('portfolio_trades.csv')
          else pd.DataFrame(columns=['date', 'action', 'ticker', 'company', 'price', 'value']))
vals = (pd.read_csv('portfolio_value.csv') if os.path.exists('portfolio_value.csv')
        else pd.DataFrame(columns=['date', 'portfolio', 'xiu']))
cash = float(state.get('cash', CAPITAL))
close = px.loc[t]

def pos_value(y, basis, basis_date):
    """Value incl. dividends since the position was last sized."""
    return basis * close[y] / px.at[pd.Timestamp(basis_date), y]


first_of_week = t.isocalendar()[1] != prev.isocalendar()[1] or t.year != prev.year
already = str(t.date()) in set(trades.date.astype(str))
start_now = len(hold) == 0 and t >= START and not state.get('started')
rebalance = (start_now or (state.get('started') and first_of_week)) and not already

if rebalance:
    rk = ranking(sc.date[sc.date < t].max())          # previous trading day's scores
    target = list(rk.index[:N])
    held = {r.yahoo: pos_value(r.yahoo, r.basis, r.basis_date) for r in hold.itertuples()}   # $ now
    value = cash + sum(held.values())
    per = value / len(target)
    traded = sum(abs(per - held.get(y, 0)) for y in target) + \
        sum(v for y, v in held.items() if y not in target)
    cost = traded * COST
    per = (value - cost) / len(target)
    old = hold.set_index('yahoo')
    rows, log = [], []
    for y in held:
        if y not in target:
            log.append({'date': str(t.date()), 'action': 'Sell', 'ticker': short(y), 'company': names.get(y, y),
                        'price': round(close[y], 2), 'value': round(held[y], 2)})
    for y in target:
        if y in held:
            rows.append({'yahoo': y, 'shares': per / close[y], 'entry_date': old.at[y, 'entry_date'],
                         'entry_price': old.at[y, 'entry_price'], 'basis': per, 'basis_date': str(t.date())})
        else:
            rows.append({'yahoo': y, 'shares': per / close[y], 'entry_date': str(t.date()),
                         'entry_price': round(close[y], 4), 'basis': per, 'basis_date': str(t.date())})
            log.append({'date': str(t.date()), 'action': 'Buy', 'ticker': short(y), 'company': names.get(y, y),
                        'price': round(close[y], 2), 'value': round(per, 2)})
    hold = pd.DataFrame(rows)
    cash = 0.0
    trades = pd.concat([trades, pd.DataFrame(log)], ignore_index=True)
    if not state.get('started'):
        state.update(started=str(t.date()))
    state['last_rebalance'] = str(t.date())
    state['last_cost'] = round(cost, 2)

state['cash'] = cash
hold.to_csv('portfolio_holdings.csv', index=False)
trades.to_csv('portfolio_trades.csv', index=False)
json.dump(state, open('portfolio_state.json', 'w'), indent=1)

# ---- daily value vs XIU ----
value = cash + float(sum(pos_value(r.yahoo, r.basis, r.basis_date) for r in hold.itertuples()))
if state.get('started'):
    xiu = CAPITAL * close['XIU.TO'] / px.at[pd.Timestamp(state['started']), 'XIU.TO']   # incl. distributions
    vals = vals[vals.date.astype(str) != str(t.date())]
    vals = pd.concat([vals, pd.DataFrame([{'date': str(t.date()), 'portfolio': round(value, 2),
                                           'xiu': round(xiu, 2)}])], ignore_index=True)
vals.to_csv('portfolio_value.csv', index=False)

# ---- holdings and provisional plan ----
rk_today = ranking(t)
rank_of = {y: i + 1 for i, y in enumerate(rk_today.index)}
now = []
for r in hold.itertuples():
    p = close[r.yahoo]
    v = pos_value(r.yahoo, r.basis, r.basis_date)
    now.append({'ticker': short(r.yahoo), 'company': names.get(r.yahoo, r.yahoo), 'since': r.entry_date,
                'entry_price': round(r.entry_price, 2), 'close': round(p, 2),
                'return_pct': round((p / px.at[pd.Timestamp(r.entry_date), r.yahoo] - 1) * 100, 2),
                'value': round(v, 2),
                'weight_pct': round(v / value * 100, 1) if value else None,
                'rank_today': rank_of.get(r.yahoo),
                'status': 'Hold' if rank_of.get(r.yahoo, 99) <= N else 'Would sell'})
pd.DataFrame(now, columns=['ticker', 'company', 'since', 'entry_price', 'close', 'return_pct', 'value',
                           'weight_pct', 'rank_today', 'status']).to_csv('portfolio_now.csv', index=False)

top = list(rk_today.index[:N])
held = set(hold.yahoo)
plan = []
for y in list(dict.fromkeys(top + list(held))):
    action = 'Hold' if (y in top and y in held) else ('Buy' if y in top else 'Sell')
    plan.append({'action': action, 'ticker': short(y), 'company': names.get(y, y), 'rank_today': rank_of.get(y),
                 'score': round(rk_today.get(y, np.nan), 3), 'rating': rating_of.get(short(y), '')})
order = {'Buy': 0, 'Sell': 1, 'Hold': 2}
plan = sorted(plan, key=lambda r: (order[r['action']], r['rank_today'] or 99))
pd.DataFrame(plan, columns=['action', 'ticker', 'company', 'rank_today', 'score', 'rating']).to_csv(
    'portfolio_plan.csv', index=False)

# next rebalance: first trading day of next week (Monday unless a holiday)
nxt = t + pd.Timedelta(days=7 - t.weekday())
if not state.get('started'):
    nxt = max(START, t + pd.Timedelta(days=1))
    while nxt.weekday() >= 5:
        nxt += pd.Timedelta(days=1)
start_val = CAPITAL
summary = {
    'as_of': str(t.date()), 'started': state.get('started', ''),
    'value': round(value, 2) if state.get('started') else None,
    'return_pct': round((value / start_val - 1) * 100, 2) if state.get('started') else None,
    'xiu_return_pct': round((vals.xiu.iloc[-1] / start_val - 1) * 100, 2) if len(vals) else None,
    'holdings': len(hold), 'last_rebalance': state.get('last_rebalance', ''),
    'traded_today': 'Yes' if rebalance else '',
    'next_rebalance': str(nxt.date()),
    'planned_buys': sum(p['action'] == 'Buy' for p in plan), 'planned_sells': sum(p['action'] == 'Sell' for p in plan),
}
pd.DataFrame([summary]).to_csv('portfolio_summary.csv', index=False)
print(json.dumps(summary, indent=1))
