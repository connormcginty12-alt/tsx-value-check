"""Benchmark ETFs with dividends reinvested (auto-adjusted closes)."""
import yfinance as yf
px = yf.download(['XIC.TO', 'XIU.TO', 'ZCN.TO', 'XEI.TO'], start='2012-01-01', auto_adjust=True, progress=False)['Close']
px.to_csv('research/benchmarks.csv', index_label='date')
print(px.tail(3))
