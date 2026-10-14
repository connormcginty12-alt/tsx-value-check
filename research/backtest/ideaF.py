import pandas as pd, numpy as np
exec(open('/home/claude/fund/bt.py').read())
h=pd.read_pickle('/home/claude/fund/hist.pkl')
P=h['P']; stocks=h['stocks']; sec={s:h['sec'].get(s,'?') for s in stocks}; RET=P.pct_change(fill_method=None); IDX=RET.index
mem=h['mem']; score=h['score']; B=pd.read_pickle('/home/claude/fund/hist_bt.pkl'); ewm=B['ewm']
sc_m=score.where(mem); secs=sorted(set(sec.values()))
secmean=pd.DataFrame({s_:sc_m[[c for c in stocks if sec[c]==s_]].mean(axis=1) for s_ in secs})
rk=secmean.rank(axis=1,ascending=False)
rot=sc_m.copy()
for c in stocks: rot[c]=sc_m[c].where(rk[sec[c]]<=3)
print('stocks eligible per day (median):',int(rot.notna().sum(axis=1).loc['2016':].median()))
# sector-level predictability: does sector mean score predict next-week sector return vs members?
fw=(np.log(P).shift(-6)-np.log(P).shift(-1)).where(mem); fw=fw.sub(fw.mean(axis=1),axis=0)
secfw=pd.DataFrame({s_:fw[[c for c in stocks if sec[c]==s_]].mean(axis=1) for s_ in secs})
ic=secmean.rank(axis=1).corrwith(secfw.rank(axis=1),axis=1).dropna().loc['2015':].iloc[::5]
print('sector-level rank corr: mean',round(ic.mean(),3),'t',round(ic.mean()/ic.std()*np.sqrt(len(ic)),2))
# run with relaxed minimum universe size
def run_relaxed(s,**kw):
    s2=s.copy(); return run(s2,**kw)
import types
r=None
dates=IDX[(IDX>='2015-01-01')]
# temporary: pad other stocks with -inf so picks only come from rot but len check passes
pad=rot.fillna(-1e9).where(mem)
r=run(pad,n=10,universe=mem).ret
s=stats(r,ewm); print('F: top 10 from 3 best sectors: CAGR',round(s['CAGR_%'],1),'vs EW',round(s['excess_%yr'],1),'years',s['years_beat'],'maxDD',round(s['max_drawdown_%'],1))
