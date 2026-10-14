# TSX value check

Every weekday after the close, GitHub Actions pulls 3 years of daily closes for ~98 of Canada's
largest stocks (`pull_tsx_prices.py`) and rates each one (`daily_rating.py`) as
**Underpriced**, **Fairly priced** or **Overpriced**, saving `ratings.csv`.

The score averages five signals, each of which predicted next-week returns relative to the other stocks
in both 2014–2020 and 2021–2026 (and the combination was positive in every calendar year 2015–2026):

1. **1-month pullback** – stocks that fell over the past month tended to bounce the next week.
2. **Peer momentum** – stocks that beat their sector peers over the past year (excluding the last month,
   after removing market moves) tended to keep doing so.
3. **Earnings surprise** – reported EPS vs analysts' expectations at the latest report (last ~3 months).
4. **Earnings-day reaction** – how the stock moved vs peers on the two days after its latest report;
   markets tend to under-react to earnings news.
5. **Earnings week** – the stock reports in the coming week (the earnings-announcement premium).

Also tested and rejected (not consistent across both periods): valuation ratios (P/E, earnings yield,
P/B — helped 2021–26, hurt 2014–20, not explained by interest-rate trends), earnings growth, dividend yield
and dividend growth, share buybacks, analyst upgrades and price-target changes, abnormal volume, ~50
price-only variants, and a gradient-boosted model (worse out of sample than simple averaging).
Financial ratios are shown in `ratings.csv` for context. Short interest (CIRO reports, Sep 2025–Sep 2026)
was tested too: heavily shorted stocks did *better* the following week, against theory, on only 24 reports
during a strong rally — not used; to be retested as reports accumulate.

**Week-ahead forecast:** `forecast_1w` = today's close × (beta × a long-run ~8%/yr market drift) × the
score's expected edge. It is essentially "no change plus a small tilt" — weekly prices are close to a coin flip.

**Live grading (`grade.py`):** every rating is saved in `ratings_history.csv` and graded once the following
week is over (`scorecard.csv`, `scorecard_summary.csv`): rank correlation with next-week returns,
Underpriced − Overpriced gap, and forecast error vs a no-change forecast. Rows before Oct 13, 2026 are a
backfill that flatters the model; only `live` rows are a true out-of-sample record.

**Paper portfolio (`portfolio.py`):** runs the backtested rule live from Oct 14, 2026 — hold the 10
S&P/TSX 60 members with the highest score, equal weight; once a week at the close of the week's first
trading day (using the previous close's scores) sell what dropped out of the top 10, buy what came in,
reset to equal size; 0.10% per trade; benchmark XIU. Files: `portfolio_*.csv`, `portfolio_state.json`.
TSX 60 membership is refreshed daily from Wikipedia (`update_tsx60.py`, `tsx60_members.csv`).

**Data being recorded for future tests (`record_data.py`):** daily analyst estimate snapshots
(`data/estimates_history.csv`), CIRO short position reports (`data/short_positions*`), and option chains
for the US listings of the ~58 interlisted names (`record_options.py`, `.github/workflows/options.yml`,
`data/options/YYYY-MM-DD.csv.gz`; recorded mid-afternoon while quotes are live — Yahoo carries no
Montréal Exchange option chains).

The edge is small (rank correlation ~0.03 with next-week returns; top-fifth minus bottom-fifth about
5–7%/yr after 10 bp trading costs in both periods) and noisy week to week.
It is a statistical tilt, not investment advice. Backtests use today's 100 largest companies,
which flatters history (survivorship bias).
