import pandas as pd, numpy as np
exec(open('/home/claude/fund/bt.py').read())
h=pd.read_pickle('/home/claude/fund/hist.pkl')
P=h['P']; stocks=h['stocks']; sec={s:h['sec'].get(s,'?') for s in stocks}; RET=P.pct_change(fill_method=None); IDX=RET.index
BM=pd.read_csv('/home/claude/repo/research/benchmarks.csv',index_col=0,parse_dates=True).reindex(IDX).ffill()
XIU=BM['XIU.TO'].pct_change(fill_method=None).fillna(0); XIC=BM['XIC.TO'].pct_change(fill_method=None).fillna(0)
mem=h['mem']; score=h['score']
dates=IDX[(IDX>='2015-01-01')&(IDX<='2026-10-13')]
# point-in-time equal weight of members (rebalanced daily, no costs)
ewm=RET.loc[dates].where(mem.loc[dates].shift(1).fillna(False)).mean(axis=1).fillna(0)
rows={}
for n in (10,15):
    for lab,kw in [('weekly',{}),('weekly, hold until out of top 25',{'buffer':25})]:
        r=run(score,n=n,universe=mem,**kw).ret
        s=stats(r,ewm); s2=stats(r,XIU)
        rows[f'top {n}, {lab}']=dict(CAGR=s['CAGR_%'],vs_members_EW=s['excess_%yr'],years_beat_EW=s['years_beat'],vs_XIU=s2['excess_%yr'],years_beat_XIU=s2['years_beat'],sharpe=s['sharpe'],maxDD=s['max_drawdown_%'])
        if n==10 and not kw: keep=r
rows['Members equal-weight (point in time)']=dict(CAGR=stats(ewm)['CAGR_%'],sharpe=stats(ewm)['sharpe'],maxDD=stats(ewm)['max_drawdown_%'],vs_XIU=stats(ewm,XIU)['excess_%yr'])
rows['XIU (TSX 60 ETF, dividends in)']=dict(CAGR=stats(XIU.loc[dates])['CAGR_%'],sharpe=stats(XIU.loc[dates])['sharpe'],maxDD=stats(XIU.loc[dates])['max_drawdown_%'])
pd.set_option('display.width',220); print(pd.DataFrame(rows).T.round(2).to_string())
yr=pd.DataFrame({'top 10':(1+keep).groupby(keep.index.year).prod()-1,'members EW':(1+ewm).groupby(ewm.index.year).prod()-1,'XIU':(1+XIU.loc[dates]).groupby(dates.year).prod()-1})*100
print(yr.round(1).T.to_string())
pd.to_pickle(dict(top10=keep,ewm=ewm,xiu=XIU.loc[dates]),'/home/claude/fund/hist_bt.pkl')
