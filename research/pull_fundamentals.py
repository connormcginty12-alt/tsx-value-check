"""One-off research pull: long price history, current fundamentals and financial statements."""
import json
import pandas as pd
import yfinance as yf

names = pd.read_csv('names.csv')
tickers = [t for t in names.tsx_ticker if t.endswith(('.TO', '.V'))]
factors = ['^GSPTSE', '^GSPC', 'CL=F', 'NG=F', 'GC=F', 'HG=F', 'CAD=X', '^TNX', '^VIX']

px = yf.download(tickers + factors, start='2012-01-01', interval='1d', auto_adjust=True, progress=False, threads=True)
px['Close'].to_csv('research/close_long.csv', index_label='date')
px['Volume'][tickers].to_csv('research/volume_long.csv', index_label='date')

FIELDS = ['currency', 'financialCurrency', 'sector', 'industry', 'marketCap', 'sharesOutstanding',
          'trailingPE', 'forwardPE', 'priceToBook', 'bookValue', 'enterpriseToEbitda', 'debtToEquity',
          'returnOnEquity', 'returnOnAssets', 'profitMargins', 'grossMargins', 'operatingMargins',
          'revenueGrowth', 'earningsGrowth', 'freeCashflow', 'operatingCashflow', 'totalDebt', 'totalCash',
          'dividendYield', 'payoutRatio', 'trailingEps', 'forwardEps', 'beta', 'heldPercentInsiders',
          'recommendationMean', 'numberOfAnalystOpinions', 'targetMeanPrice']
info_rows, stmts = [], []
for t in tickers:
    tk = yf.Ticker(t)
    try:
        info = tk.info
        info_rows.append({'ticker': t, **{f: info.get(f) for f in FIELDS}})
    except Exception as exc:
        print('info failed', t, exc)
    for kind, getter in [('income_annual', lambda: tk.income_stmt), ('balance_annual', lambda: tk.balance_sheet),
                         ('cashflow_annual', lambda: tk.cashflow), ('income_quarterly', lambda: tk.quarterly_income_stmt),
                         ('balance_quarterly', lambda: tk.quarterly_balance_sheet),
                         ('cashflow_quarterly', lambda: tk.quarterly_cashflow)]:
        try:
            df = getter()
            if df is None or df.empty:
                continue
            long = df.stack().reset_index()
            long.columns = ['item', 'period_end', 'value']
            long['ticker'] = t
            long['kind'] = kind
            stmts.append(long)
        except Exception as exc:
            print(kind, 'failed', t, exc)
pd.DataFrame(info_rows).to_csv('research/info_now.csv', index=False)
pd.concat(stmts).to_csv('research/statements.csv', index=False)
print('done', len(info_rows), 'info rows,', sum(len(s) for s in stmts), 'statement values')
