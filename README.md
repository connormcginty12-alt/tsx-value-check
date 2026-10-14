# TSX value check

Every weekday after the close, GitHub Actions pulls 3 years of daily closes for ~98 of Canada's
largest stocks (`pull_tsx_prices.py`) and rates each one (`daily_rating.py`) as
**Underpriced**, **Fairly priced** or **Overpriced**, saving `ratings.csv`.

The score averages four signals, each of which predicted next-week returns relative to the other stocks
in both 2014–2020 and 2021–2026 (and the combination was positive in every calendar year 2014–2026):

1. **1-month pullback** – stocks that fell over the past month tended to bounce the next week.
2. **Peer momentum** – stocks that beat their sector peers over the past year (excluding the last month,
   after removing market moves) tended to keep doing so.
3. **Earnings surprise** – reported EPS vs analysts' expectations at the latest report (last ~3 months).
4. **Earnings-day reaction** – how the stock moved vs peers on the two days after its latest report;
   markets tend to under-react to earnings news.

Valuation ratios (P/E, earnings yield, P/B) and earnings growth were tested too: they helped in 2021–2026
but hurt in 2014–2020, so they are shown in `ratings.csv` for context rather than used in the score.

The edge is small (rank correlation ~0.027 with next-week returns) and noisy week to week.
It is a statistical tilt, not investment advice. Backtests use today's 100 largest companies,
which flatters history (survivorship bias).
