import pandas as pd, numpy as np
exec(open('/home/claude/fund/bt.py').read())
h=pd.read_pickle('/home/claude/fund/hist.pkl')
P=h['P']; stocks=h['stocks']; sec={s:h['sec'].get(s,'?') for s in stocks}; RET=P.pct_change(fill_method=None); IDX=RET.index
mem=h['mem']; score=h['score']; B=pd.read_pickle('/home/claude/fund/hist_bt.pkl'); ewm=B['ewm']
BM=pd.read_csv('/home/claude/repo/research/benchmarks.csv',index_col=0,parse_dates=True).reindex(IDX).ffill()
XIU=BM['XIU.TO'].pct_change(fill_method=None).fillna(0)
def summ(name,r):
    s=stats(r,ewm); return dict(idea=name,CAGR=s['CAGR_%'],vs_EW=s['excess_%yr'],years_beat=s['years_beat'],sharpe=s['sharpe'],maxDD=s['max_drawdown_%'],
        y2022=((1+r.loc['2022']).prod()-1)*100, y2020=((1+r.loc['2020']).prod()-1)*100)
rows=[summ('baseline: top 10 weekly',B['top10'])]
vol=RET.rolling(63).std()
# A) exclude the most volatile third of members before picking
vrank=vol.where(mem).rank(axis=1,pct=True)
rows.append(summ('A: skip most volatile third',run(score.where(vrank<=0.67),n=10,universe=mem).ret))
# B) risk-adjusted score: score / volatility rank-scaled
rows.append(summ('B: score minus 0.5 x volatility z',run(score-0.5*((vol-vol.where(mem).mean(axis=1).values[:,None])/vol.where(mem).std(axis=1).values[:,None]),n=10,universe=mem).ret))
# C) sector cap 3
rows.append(summ('C: max 3 per sector',run(score,n=10,universe=mem,sector_cap=3).ret))
rows.append(summ('C2: max 2 per sector',run(score,n=10,universe=mem,sector_cap=2).ret))
# D) volatility-managed exposure: scale baseline daily return by target/realised vol (known yesterday), cap 1.0
base=B['top10']; rv=base.rolling(21).std().shift(1)*np.sqrt(252); lev=(0.15/rv).clip(upper=1.0).fillna(1.0)
rows.append(summ('D: cut exposure when strategy vol > 15% (cash otherwise)',base*lev))
# E) trend filter
rows.append(summ('E: cash when XIU < 200-day avg',run(score,n=10,universe=mem,trend_filter=True).ret))
# F) sector rotation: rank sectors by average member score, buy top-score stocks from top 3 sectors
sc_m=score.where(mem)
secs=pd.Series(sec)
secmean=pd.DataFrame({s_:sc_m[[c for c in stocks if sec[c]==s_]].mean(axis=1) for s_ in secs.unique()})
rot=pd.DataFrame(np.nan,index=score.index,columns=stocks)
top3=secmean.rank(axis=1,ascending=False)<=3
for s_ in secs.unique():
    cols=[c for c in stocks if sec[c]==s_]; rot[cols]=sc_m[cols].where(top3[s_].values[:,None].repeat(len(cols),1))
rows.append(summ('F: only stocks from the 3 best-scoring sectors',run(rot,n=10,universe=mem).ret))
# G) blend: 50% strategy + 50% XIU
rows.append(summ('G: 50% strategy + 50% XIU',0.5*base+0.5*XIU.reindex(base.index).fillna(0)))
df=pd.DataFrame(rows); pd.set_option('display.width',220); print(df.round(2).to_string(index=False))
df.to_csv('/home/claude/fund/ideas.csv',index=False)
