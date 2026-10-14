import pandas as pd, numpy as np
exec(open('/home/claude/fund/bt.py').read())
h=pd.read_pickle('/home/claude/fund/hist.pkl')
P=h['P']; stocks=h['stocks']; sec={s:h['sec'].get(s,'?') for s in stocks}; RET=P.pct_change(fill_method=None); IDX=RET.index
mem=h['mem']; score=h['score']; B=pd.read_pickle('/home/claude/fund/hist_bt.pkl'); ewm=B['ewm']
# 1) which stocks drove it: rerun capturing weights by re-deciding picks each rebalance (top 10 weekly)
dates=IDX[(IDX>='2015-01-01')&(IDX<='2026-10-13')]
picks={}
for k,d in enumerate(dates):
    if k%5: continue
    s=score.loc[d][mem.loc[d]].dropna()
    if len(s)>=30: picks[d]=list(s.nlargest(10).index)
contrib={}
pk=sorted(picks)
for a,b in zip(pk,pk[1:]+[dates[-1]]):
    i0=IDX.get_loc(a)+1; i1=IDX.get_loc(b)+1
    seg=RET.iloc[i0+1:i1+1]
    memb=list(mem.columns[mem.loc[a]]); bench=((1+seg[memb].fillna(0)).prod()-1).mean()
    for t in picks[a]:
        r=(1+seg[t].fillna(0)).prod()-1
        rel=r-bench
        contrib.setdefault((t,a.year),[]).append(rel/10)
c=pd.Series({k:sum(v) for k,v in contrib.items()})
by_stock=c.groupby(level=0).sum().sort_values()
print('Top contributors to excess (sum of weekly excess x weight, %):'); print((by_stock.tail(8)*100).round(1).to_string())
print('Worst:'); print((by_stock.head(6)*100).round(1).to_string())
print('2016 top:',(c.xs(2016,level=1).sort_values().tail(4)*100).round(1).to_dict())
print('2022 worst:',(c.xs(2022,level=1).sort_values().head(4)*100).round(1).to_dict())
print('total excess sum %:',round(by_stock.sum()*100,1),' without top 3 stocks:',round(by_stock.iloc[:-3].sum()*100,1))
# 2) random portfolios: 10 random members each week, same schedule & costs
rng=np.random.default_rng(7); res=[]
for k in range(200):
    rs=pd.DataFrame(rng.random(score.shape),index=score.index,columns=score.columns).where(score.notna())
    r=run(rs,n=10,universe=mem).ret; res.append(stats(r)['CAGR_%'])
strat=stats(B['top10'])['CAGR_%']
res=np.array(res); print(f'random 10-stock portfolios: median CAGR {np.median(res):.1f}%, 95th pct {np.percentile(res,95):.1f}%, best {res.max():.1f}%; strategy {strat:.1f}% beats {np.mean(res<strat)*100:.1f}% of them')
# 3) start-date sensitivity: excess vs members EW for each start year to end
for y in range(2015,2025,2):
    r=B['top10'].loc[f'{y}-01-01':]; e=ewm.loc[f'{y}-01-01':]
    print('start',y,'CAGR',round(stats(r)['CAGR_%'],1),'vs EW',round(stats(r,e)['excess_%yr'],1))
# 4) costs
for c_ in (5,10,20,30): print('cost',c_,'bp: CAGR',round(stats(run(score,n=10,universe=mem,cost_bp=c_).ret)['CAGR_%'],1))
