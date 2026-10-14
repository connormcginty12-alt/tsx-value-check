import pandas as pd, numpy as np
h=pd.read_pickle('/home/claude/fund/hist.pkl'); P=h['P']; mem=h['mem']; score=h['score']
d=pd.read_csv('/home/claude/repo/research/close_long.csv',index_col=0,parse_dates=True)
fw=(np.log(P).shift(-6)-np.log(P).shift(-1)).where(mem); fw=fw.sub(fw.mean(axis=1),axis=0)
ic=score.rank(axis=1).corrwith(fw.rank(axis=1),axis=1).dropna().loc['2015':'2026-10-01']
wk=ic.iloc[::5]
vix=d['^VIX'].reindex(ic.index).ffill(); tsx=np.log(d['^GSPTSE'].reindex(ic.index).ffill())
tnx=d['^TNX'].reindex(ic.index).ffill()
def show(name,flag):
    f=flag.reindex(wk.index)
    for v in sorted(f.dropna().unique()):
        s=wk[f==v]; print(f'  {name}={v}: rank corr {s.mean():.3f} (weeks {len(s)}, t={s.mean()/s.std()*np.sqrt(len(s)):.2f})')
print('By VIX level:'); show('VIX', pd.cut(vix,[0,15,20,30,100],labels=['<15','15-20','20-30','>30']).astype(str))
print('By TSX trend (above 200-day avg):'); show('TSX up-trend', (tsx>tsx.rolling(200).mean()))
print('By 10y yield change over 6 months:'); show('yields rising', (tnx-tnx.shift(126))>0)
print('By earnings season (Feb/May/Aug/Nov vs other):'); show('earnings month', pd.Series(ic.index.month.isin([2,5,8,11]),index=ic.index))
print('By year:'); print(wk.groupby(wk.index.year).mean().round(3).to_dict())
