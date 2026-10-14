import pandas as pd, numpy as np, json, re, glob
snap=json.load(open('/home/claude/fund/tsx60_snap.json'))
H=pd.read_csv('/home/claude/repo/research/hist_close.csv',index_col=0,parse_dates=True)
Fz=pd.read_csv('/home/claude/repo/research/hist_factors.csv',index_col=0,parse_dates=True)
days=Fz['^GSPTSE'].dropna().index; days=days[(days>='2012-06-01')&(days<='2026-10-13')]
P=H.reindex(days); stocks=[c for c in P.columns if P[c].notna().sum()>250]; P=P[stocks]
# GICS sector: most recent label seen for each ticker
sec={}
for d in sorted(snap):
    for t,name,s in snap[d]: sec[t]=s.split('<')[0].strip()
NORM={'Basic Materials':'Materials','Financial Services':'Financials','Healthcare':'Health Care','Technology':'Tech',
      'Information Technology':'Tech','Consumer Cyclical':'Consumer Discretionary','Telecommunication Services':'Communication Services'}
sec={k:NORM.get(v,v) for k,v in sec.items()}
# membership per day (latest snapshot on or before the day)
mem=pd.DataFrame(False,index=days,columns=stocks)
for d in sorted(snap):
    lst={t for t,_,_ in snap[d]}
    mem.loc[mem.index>=pd.Timestamp(d),:]=False
    for t in lst:
        if t in mem: mem.loc[mem.index>=pd.Timestamp(d),t]=True
mem=mem&P.notna()
print('members with data per day (median by year):',mem.sum(axis=1).groupby(mem.index.year).median().to_dict())
print('sectors:',pd.Series(sec).value_counts().to_dict())
LP=np.log(P); R=LP.diff(); TSX=np.log(Fz['^GSPTSE'].reindex(days)).diff()
beta=pd.DataFrame({s:R[s].rolling(252,min_periods=120).cov(TSX)/TSX.rolling(252,min_periods=120).var() for s in stocks}).shift(1)
e=R-beta.mul(TSX,axis=0)
res=pd.DataFrame({s:e[s]-e[[p for p in stocks if sec.get(p)==sec.get(s) and p!=s]].mean(axis=1) for s in stocks})
c=R.fillna(0).cumsum(); pull=-(c-c.shift(21)).where(P.notna())
cr=res.fillna(0).cumsum(); pmom=(cr.shift(21)-cr.shift(252)).where(P.notna())
# earnings
E=pd.read_csv('/home/claude/repo/research/hist_earnings.csv'); E['dt']=pd.to_datetime(E.datetime,utc=True).dt.tz_convert('America/Toronto')
idx=days; idx_ext=idx.append(pd.bdate_range(idx[-1]+pd.Timedelta(days=1),periods=30))
def eff(ts,dd=idx_ext):
    d0=pd.Timestamp(ts.date()); i=dd.searchsorted(d0 if ts.hour+ts.minute/60<9.5 else d0+pd.Timedelta(days=1)); return dd[i] if i<len(dd) else pd.NaT
E['eff']=E.dt.map(eff); E=E.dropna(subset=['eff'])
sue=pd.DataFrame(np.nan,index=idx,columns=stocks); ear=sue.copy(); due=pd.DataFrame(0.0,index=idx,columns=stocks)
for t,grp in E.groupby('wiki_ticker'):
    if t not in stocks: continue
    j=stocks.index(t)
    for _,r in grp.drop_duplicates('eff').iterrows():
        i=idx_ext.get_loc(r.eff); lo,hi=max(0,i-6),min(len(idx),max(0,i-1))
        if lo<hi: due.iloc[lo:hi,j]=1.0
        if i>=len(idx) or pd.isna(r.eps_reported) or pd.isna(r.eps_estimate): continue
        sue.iloc[i,j]=np.clip((r.eps_reported-r.eps_estimate)/max(abs(r.eps_estimate),0.05),-1,1)
        if i+1<len(idx) and i>=1: ear.iloc[i+1,j]=cr[t].iloc[i+1]-cr[t].iloc[i-1]
sue=sue.ffill(limit=62); ear=ear.ffill(limit=62); due=due.where(P.notna())
# z-scores computed WITHIN the members of that day
def z(x):
    x=x.where(mem); return x.sub(x.mean(axis=1),axis=0).div(x.std(axis=1),axis=0).clip(-3,3)
zf=lambda x:z(x).fillna(0).where(mem)
score=((z(pull).fillna(0)+z(pmom).fillna(0)+zf(sue)+zf(ear)+zf(due))/5).where(mem&pull.notna()&pmom.notna())
pd.to_pickle(dict(P=P,score=score,mem=mem,sec=sec,stocks=stocks,R=R),'/home/claude/fund/hist.pkl')
print('scored per day (median):',int(score.notna().sum(axis=1).loc['2015':].median()), '| earnings coverage:',E.wiki_ticker.nunique())
