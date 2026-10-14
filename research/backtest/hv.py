import pandas as pd, numpy as np
exec(open('/home/claude/fund/bt.py').read())
h=pd.read_pickle('/home/claude/fund/hist.pkl')
P=h['P']; stocks=h['stocks']; sec={s:h['sec'].get(s,'?') for s in stocks}; RET=P.pct_change(fill_method=None); IDX=RET.index
mem=h['mem']; score=h['score']; B=pd.read_pickle('/home/claude/fund/hist_bt.pkl'); x=B['xiu']; ew=B['ewm']
vol=RET.rolling(63).std(); vr=vol.where(mem).rank(axis=1,pct=True)
rng=np.random.default_rng(1)
# random 10 from the most volatile third each week (same exposure to risk, no score)
rs=(vr.where(vr>0.67)*0+pd.DataFrame(rng.random(vr.shape),index=vr.index,columns=vr.columns)).fillna(-1e9).where(mem)
hv=run(rs,n=10,universe=mem).ret
# score picks restricted to mid+high vol two-thirds
sm=score.where(vr>0.34).fillna(-1e9).where(mem)
smr=run(sm,n=10,universe=mem).ret
wx=(1+x).resample('W-FRI').prod()-1; X=np.column_stack([np.ones(len(wx)),wx.values])
for lab,r in [('random 10 from most volatile third',hv),('score top 10 within mid+high volatility',smr),('score top 10 (baseline)',B['top10'])]:
    wr=((1+r).resample('W-FRI').prod()-1).reindex(wx.index).fillna(0); b=np.linalg.lstsq(X,wr.values,rcond=None)[0]
    s=stats(r,ew); print(f'{lab}: CAGR {s["CAGR_%"]:.1f}%, vs EW {s["excess_%yr"]:.1f}, years {s["years_beat"]}, beta {b[1]:.2f}, alpha vs XIU {b[0]*52*100:.1f}%/yr, maxDD {s["max_drawdown_%"]:.1f}')
