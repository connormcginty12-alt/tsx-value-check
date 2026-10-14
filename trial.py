"""One-month paper-money trial for Connor: $1,000 on Wealthsimple terms.

Same picks as the paper portfolio (top 10 S&P/TSX 60 members by score, using the previous close's
scores), but set up the way a small Wealthsimple account would run it:
  - $1,000 start, fractional shares, no commissions (Wealthsimple: free trades, fractional shares
    on thousands of TSX stocks)
  - first buys at the close on START; then once a week at the close of the week's first trading
    day: sell anything that dropped out of the top 10 and split the proceeds equally across the
    new entries (no trimming/topping-up of positions that stay)
  - trading stops after END; the final value is marked at END's close
Every move is logged in trial_trades.csv with shares, price, cost basis and realised profit/loss.
Outputs: trial_trades.csv, trial_holdings.csv, trial_value.csv, trial_summary.csv, trial_state.json.
"""
import json
import os

import pandas as pd

START = pd.Timestamp('2026-10-14')
END = pd.Timestamp('2026-11-13')
N = 10
CAPITAL = 1000.0

px = pd.read_csv('tsx100_closes.csv', index_col=0, parse_dates=True)
px = px[px['^GSPTSE'].notna()]
days = px.index
t, prev = days[-1], days[-2]
members = pd.read_csv('tsx60_members.csv')
names = dict(zip(members.yahoo, members.company))
sc = pd.read_csv('portfolio_scores.csv', parse_dates=['date'])
sc = sc[sc.yahoo.isin(members.yahoo)]
short = lambda y: y.replace('.TO', '').replace('.V', '')
close = px.loc[t]

state = json.load(open('trial_state.json')) if os.path.exists('trial_state.json') else {}
hold = (pd.read_csv('trial_holdings.csv') if os.path.exists('trial_holdings.csv')
        else pd.DataFrame(columns=['yahoo', 'shares', 'cost', 'entry_date']))
trades = (pd.read_csv('trial_trades.csv') if os.path.exists('trial_trades.csv')
          else pd.DataFrame(columns=['date', 'action', 'ticker', 'company', 'shares', 'price', 'amount',
                                     'cost_basis', 'profit_loss', 'reason']))
vals = (pd.read_csv('trial_value.csv') if os.path.exists('trial_value.csv')
        else pd.DataFrame(columns=['date', 'trial', 'xiu', 'cash']))
cash = float(state.get('cash', CAPITAL))

if t > END and state.get('finished'):
    print('Trial finished on', state['finished'], '— nothing to do')
    raise SystemExit(0)


def ranking(day):
    s = sc[sc.date == day].set_index('yahoo').score
    s = s[[y for y in s.index if y in px and pd.notna(px.at[t, y])]]
    return s.sort_values(ascending=False)


first_of_week = t.isocalendar()[1] != prev.isocalendar()[1] or t.year != prev.year
already = str(t.date()) in set(trades.date.astype(str))
in_window = START <= t <= END
start_now = len(hold) == 0 and in_window and not state.get('started')
rebalance = in_window and (start_now or (state.get('started') and first_of_week)) and not already
log = []

if rebalance:
    sig_day = sc.date[sc.date < t].max()
    rk = ranking(sig_day)
    rank_of = {y: i + 1 for i, y in enumerate(rk.index)}
    target = list(rk.index[:N])
    held = list(hold.yahoo)
    rows = {r.yahoo: r._asdict() for r in hold.itertuples(index=False)}
    # 1. sell what dropped out
    for y in held:
        if y not in target:
            r = rows.pop(y)
            amt = r['shares'] * close[y]
            log.append({'date': str(t.date()), 'action': 'Sell', 'ticker': short(y), 'company': names.get(y, y),
                        'shares': round(r['shares'], 4), 'price': round(close[y], 2), 'amount': round(amt, 2),
                        'cost_basis': round(r['cost'], 2), 'profit_loss': round(amt - r['cost'], 2),
                        'reason': f"Fell to #{rank_of.get(y, '–')} on {sig_day.date()} (out of top {N})"})
            cash += amt
    # 2. buy the new entries with all available cash, split equally
    new = [y for y in target if y not in rows]
    if new:
        per = cash / len(new)
        for y in new:
            sh = per / close[y]
            rows[y] = {'yahoo': y, 'shares': sh, 'cost': per, 'entry_date': str(t.date())}
            log.append({'date': str(t.date()), 'action': 'Buy', 'ticker': short(y), 'company': names.get(y, y),
                        'shares': round(sh, 4), 'price': round(close[y], 2), 'amount': round(per, 2),
                        'cost_basis': round(per, 2), 'profit_loss': None,
                        'reason': f"Ranked #{rank_of[y]} on {sig_day.date()}"})
        cash = 0.0
    hold = pd.DataFrame(list(rows.values()), columns=['yahoo', 'shares', 'cost', 'entry_date'])
    trades = pd.concat([trades, pd.DataFrame(log)], ignore_index=True)
    if not state.get('started'):
        state.update(started=str(t.date()), xiu_start=float(close['XIU.TO']))
    state['last_rebalance'] = str(t.date())

value = cash + float(sum(r.shares * close[r.yahoo] for r in hold.itertuples()))
if state.get('started') and t <= END:
    xiu = CAPITAL * close['XIU.TO'] / state['xiu_start']
    vals = vals[vals.date.astype(str) != str(t.date())]
    vals = pd.concat([vals, pd.DataFrame([{'date': str(t.date()), 'trial': round(value, 2), 'xiu': round(xiu, 2),
                                           'cash': round(cash, 2)}])], ignore_index=True)
if t >= END and state.get('started'):
    state['finished'] = str(min(t, END).date())
state['cash'] = cash

hold.to_csv('trial_holdings.csv', index=False)
trades.to_csv('trial_trades.csv', index=False)
vals.to_csv('trial_value.csv', index=False)
json.dump(state, open('trial_state.json', 'w'), indent=1)

realised = pd.to_numeric(trades.profit_loss, errors='coerce').sum() if len(trades) else 0.0
unrealised = float(sum(r.shares * close[r.yahoo] - r.cost for r in hold.itertuples()))
summary = {'as_of': str(t.date()), 'started': state.get('started', ''), 'ends': str(END.date()),
           'value': round(value, 2), 'profit_loss': round(value - CAPITAL, 2),
           'return_pct': round((value / CAPITAL - 1) * 100, 2),
           'xiu_return_pct': round((vals.xiu.iloc[-1] / CAPITAL - 1) * 100, 2) if len(vals) else None,
           'realised_pl': round(realised, 2), 'unrealised_pl': round(unrealised, 2),
           'moves': len(trades), 'traded_today': 'Yes' if rebalance else '',
           'finished': state.get('finished', '')}
pd.DataFrame([summary]).to_csv('trial_summary.csv', index=False)
print(json.dumps(summary, indent=1))
