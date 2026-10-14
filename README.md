# TSX value check

Every weekday after the close, GitHub Actions pulls 3 years of daily closes for ~98 of Canada's
largest stocks (`pull_tsx_prices.py`) and rates each one (`daily_rating.py`) as
**Underpriced**, **Fairly priced** or **Overpriced**, saving `ratings.csv`.

The score averages two metrics that predicted next-week relative returns in a 2021–2026 backtest:

1. **1-month pullback** – stocks that fell over the past month tended to bounce the next week.
2. **Peer momentum** – stocks that beat their sector peers over the past year (excluding the last month,
   after removing market moves) tended to keep doing so.

The edge is small (rank correlation ~0.03–0.04 with next-week returns) and noisy week to week.
It is a statistical tilt, not investment advice.
