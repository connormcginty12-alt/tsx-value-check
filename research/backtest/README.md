# Backtest (run Oct 14, 2026)

Portfolio simulation of the five-signal score, 2015–2026. Scripts were run in Claude's workspace
(paths point there); inputs come from `research/` (prices, earnings, TSX 60 history, benchmark ETFs).

- `hist_univ.py` – point-in-time S&P/TSX 60 universe (Wikipedia member lists 2014–2023; 71 of 88 past
  members have Yahoo prices — the 17 missing were takeovers/mergers) and the score rebuilt on it.
- `bt.py` – engine: decide at close t, trade at close t+1, 10 bp per trade, weights drift, dividends in.
- `run_hist.py`, `export_bt.py` – main results and dashboard tables (`bt_*.csv`).
- `robust.py`, `rand0.py`, `alpha.py`, `hv.py`, `regime2.py`, `ideas.py`, `ideaF.py` – robustness checks
  and ideas (see `bt_checks.csv`).

Main result (top 10 weekly, point-in-time TSX 60): 19.4%/yr vs 13.0% for the members' equal-weight
average and 11.2% for XIU; ahead of the members in 10 of 12 years; worst drawdown −43%; 2022 −30%.
Beat all 80 random 10-stock portfolios before costs; risk-adjusted alpha +6.7%/yr (t = 1.86).
Very sensitive to trading costs (9.9%/yr at 30 bp per trade).
