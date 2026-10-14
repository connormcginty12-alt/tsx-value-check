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
Financial ratios are shown in `ratings.csv` for context.

The edge is small (rank correlation ~0.03 with next-week returns; top-fifth minus bottom-fifth about
5–7%/yr after 10 bp trading costs in both periods) and noisy week to week.
It is a statistical tilt, not investment advice. Backtests use today's 100 largest companies,
which flatters history (survivorship bias).
