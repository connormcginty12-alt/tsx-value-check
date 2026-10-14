import pandas as pd, numpy as np
exec(open('/home/claude/fund/bt.py').read())
h=pd.read_pickle('/home/claude/fund/hist.pkl')
P=h['P']; stocks=h['stocks']; sec={s:h['sec'].get(s,'?') for s in stocks}; RET=P.pct_change(fill_method=None); IDX=RET.index
mem=h['mem']; score=h['score']; B=pd.read_pickle('/home/claude/fund/hist_bt.pkl')
r=B['top10']; x=B['xiu'].reindex(r.index).fillna(0); ew=B['ewm']
# CAPM alpha with weekly returns (reduces close-time noise)
wr=(1+r).resample('W-FRI').prod()-1; wx=(1+x).resample('W-FRI').prod()-1
X=np.column_stack([np.ones(len(wx)),wx.values]); b=np.linalg.lstsq(X,wr.values,rcond=None)[0]
resid=wr.values-X@b; se=np.sqrt(np.sum(resid**2)/(len(wr)-2)/np.sum((wx-wx.mean())**2)); 
a_se=np.sqrt(np.sum(resid**2)/(len(wr)-2)*(1/len(wr)+wx.mean()**2/np.sum((wx-wx.mean())**2)))
print(f'Top 10 vs XIU: beta {b[1]:.2f}, alpha {b[0]*52*100:.1f}%/yr (t={b[0]/a_se:.2f})')
# same for the members' high-volatility third (a pure 'risk' portfolio) to compare
vol=RET.rolling(63).std(); vr=vol.where(mem).rank(axis=1,pct=True)
hv=run(vr.where(vr>0.67),n=10,universe=mem).ret
wh=(1+hv).resample('W-FRI').prod()-1; bh=np.linalg.lstsq(X,wh.reindex(wx.index).fillna(0).values,rcond=None)[0]
print(f'Most-volatile-10 (no score) vs XIU: beta {bh[1]:.2f}, alpha {bh[0]*52*100:.1f}%/yr, CAGR {stats(hv)["CAGR_%"]:.1f}%')
# score's edge WITHIN volatility buckets: rank corr of score with next-week return inside low/mid/high vol thirds
fw=(np.log(P).shift(-6)-np.log(P).shift(-1)).where(mem); fw=fw.sub(fw.mean(axis=1),axis=0)
for lo,hi,lab in [(0,0.34,'low vol'),(0.34,0.67,'mid vol'),(0.67,1.01,'high vol')]:
    m=(vr>lo)&(vr<=hi)
    ic=score.where(m).rank(axis=1).corrwith(fw.where(m).rank(axis=1),axis=1).dropna().loc['2015':].iloc[::5]
    print(f'{lab}: rank corr {ic.mean():.3f} (t={ic.mean()/ic.std()*np.sqrt(len(ic)):.2f})')
# staggered: 4 sub-portfolios each held 4 weeks, one rebalanced each week (cuts turnover)
subs=[run(score,n=10,universe=mem,every=20,start=str(IDX[IDX>='2015-01-01'][5*k].date())).ret for k in range(4)]
st=pd.concat(subs,axis=1).fillna(0).mean(axis=1)
s=stats(st,ew); print(f'Staggered 4 x 4-week books: CAGR {s["CAGR_%"]:.1f}%, vs EW {s["excess_%yr"]:.1f}, years {s["years_beat"]}, maxDD {s["max_drawdown_%"]:.1f}')
