import pandas as pd, numpy as np
exec(open('/home/claude/fund/bt.py').read())
h=pd.read_pickle('/home/claude/fund/hist.pkl')
P=h['P']; stocks=h['stocks']; sec={s:h['sec'].get(s,'?') for s in stocks}; RET=P.pct_change(fill_method=None); IDX=RET.index
mem=h['mem']; score=h['score']; B=pd.read_pickle('/home/claude/fund/hist_bt.pkl')
r,ew,x=B['top10'],B['ewm'],B['xiu'].reindex(B['top10'].index).fillna(0)
cur=pd.DataFrame({'strategy':(1+r).cumprod(),'members_equal_weight':(1+ew).cumprod(),'xiu':(1+x).cumprod()})*10000
cur=cur.resample('W-FRI').last().dropna(); cur.index=cur.index.strftime('%Y-%m-%d')
cur.round(0).to_csv('/home/claude/fund/out/bt_curves.csv',index_label='date')
dd=pd.DataFrame({k:(v/v.cummax()-1)*100 for k,v in {'strategy':(1+r).cumprod(),'xiu':(1+x).cumprod()}.items()}).resample('W-FRI').min()
dd.index=dd.index.strftime('%Y-%m-%d'); dd.round(1).to_csv('/home/claude/fund/out/bt_drawdowns.csv',index_label='date')
yr=pd.DataFrame({'strategy':(1+r).groupby(r.index.year).prod()-1,'members_equal_weight':(1+ew).groupby(ew.index.year).prod()-1,'xiu':(1+x).groupby(x.index.year).prod()-1})*100
yr['beat_members']=np.where(yr.strategy>yr.members_equal_weight,'Yes','No'); yr.index.name='year'
yr.round(1).to_csv('/home/claude/fund/out/bt_years.csv')
V=[]
def add(name,rr):
    s=stats(rr,ew); s2=stats(rr,x)
    V.append(dict(variant=name,cagr_pct=s['CAGR_%'],vs_members_pct_yr=s['excess_%yr'],years_beat_members=s['years_beat'],vs_xiu_pct_yr=s2['excess_%yr'],sharpe=s['sharpe'],max_drawdown_pct=s['max_drawdown_%']))
add('Top 10, weekly (main)',r)
add('Top 15, weekly',run(score,n=15,universe=mem).ret)
add('Top 10, hold until out of top 25',run(score,n=10,universe=mem,buffer=25).ret)
add('Top 10, max 3 per sector',run(score,n=10,universe=mem,sector_cap=3).ret)
add('Top 10, cash when XIU below 200-day avg',run(score,n=10,universe=mem,trend_filter=True).ret)
rv=r.rolling(21).std().shift(1)*np.sqrt(252); add('Top 10, cut exposure when volatile',r*(0.15/rv).clip(upper=1).fillna(1))
add('50% top 10 + 50% XIU',0.5*r+0.5*x)
add('Top 10, weekly, costs 20 bp',run(score,n=10,universe=mem,cost_bp=20).ret)
add('Members equal-weight (benchmark)',ew)
add('XIU, TSX 60 ETF (benchmark)',x)
pd.DataFrame(V).round(2).to_csv('/home/claude/fund/out/bt_variants.csv',index=False)
print(pd.DataFrame(V).round(2).to_string(index=False)); print(yr.round(1).to_string())
