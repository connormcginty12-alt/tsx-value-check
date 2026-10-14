import pandas as pd, numpy as np
exec(open('/home/claude/fund/bt.py').read())
h=pd.read_pickle('/home/claude/fund/hist.pkl')
P=h['P']; stocks=h['stocks']; sec={s:h['sec'].get(s,'?') for s in stocks}; RET=P.pct_change(fill_method=None); IDX=RET.index
mem=h['mem']; score=h['score']
strat=stats(run(score,n=10,universe=mem,cost_bp=0).ret)['CAGR_%']
rng=np.random.default_rng(11); res=[]
for k in range(80):
    rs=pd.DataFrame(rng.random(score.shape),index=score.index,columns=score.columns).where(score.notna())
    res.append(stats(run(rs,n=10,universe=mem,cost_bp=0).ret)['CAGR_%'])
res=np.array(res)
print(f'No costs: strategy {strat:.1f}%/yr; 80 random 10-stock weekly portfolios: median {np.median(res):.1f}%, 95th pct {np.percentile(res,95):.1f}%, best {res.max():.1f}%; strategy beats {np.mean(res<strat)*100:.0f}%')
